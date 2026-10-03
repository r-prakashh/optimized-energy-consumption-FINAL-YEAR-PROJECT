"""Volt — the WattWise smart assistant.

Two engines behind one endpoint:

* **Claude (when credentials are configured)** — a tool-using assistant. It
  doesn't do energy arithmetic in its head: it calls the same estimators the
  rest of the app uses (`estimate_appliance_change`, `estimate_bill_cost`), so
  its numbers match the planner and simulator exactly. The user's current
  page context (bill analysis, last plan) is passed in so answers are
  personal ("your May bill") rather than generic.
* **Offline rule engine (always available)** — intent matching + the same
  estimators, so the assistant still answers the common questions (tariff,
  "what if I add an AC for 6 hours", forecast, tips) on a free deployment
  with no API key.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.config import APPLIANCE_CATALOG, estimate_cost, settings
from app.core.llm import CLAUDE_MODEL, FALLBACK_BODY, FALLBACK_HEADERS, get_client
from app.ml.models.appliance_model import ApplianceModel
from app.optimization.scenario import ApplianceChange, simulate

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4
DEFAULT_BASELINE_KWH = 250.0

_catalog_lines = "\n".join(
    f"- {k}: {v['label']}, ~{v['avg_watts']} W typical" for k, v in APPLIANCE_CATALOG.items()
)
_slab_lines = "\n".join(
    f"- up to {'∞' if t == float('inf') else int(t)} kWh/month: ₹{r:.2f}/kWh" for t, r in settings.tariff_slabs
)

SYSTEM_PROMPT = f"""You are Volt, the friendly energy assistant inside WattWise — a web app that helps \
Tamil Nadu households forecast electricity use, read their past bills, and plan appliance usage to a budget.

What the app offers (point users to these when relevant):
- Bill Insights page (/bills): upload past electricity bills (PDF, photo, or a handwritten log), OCR reads \
units and amounts, then an ML model finds the trend, flags unusual months, forecasts the next 3 months and \
gives saving advice.
- Appliance What-If (/simulator): add or remove appliances and see the change in monthly units and bill.
- Planner (/plan): budget + appliances -> forecast, TNEB cost estimate, and recommended hours per appliance.
- Methodology (/methodology): how the models work.

Tariff used everywhere (TNEB domestic LT-IA, monthly-equivalent slabs, telescopic; real TNEB bills are \
bi-monthly so the thresholds double on a bill):
{_slab_lines}

Appliance categories the estimators understand:
{_catalog_lines}

Rules:
- For any number about energy or cost, call the tools rather than estimating mentally, so your answer \
matches the rest of the app.
- Be concise and practical: 2-6 short sentences or a tight bullet list. Use ₹ and kWh ("units").
- Estimates are planning figures, not meter-accurate billing — say so if the user treats them as exact.
- Stay on household energy, bills, appliances and using this app. Politely decline unrelated requests."""

TOOLS = [
    {
        "name": "estimate_appliance_change",
        "description": (
            "Estimate how adding and/or removing appliances changes the household's monthly kWh and TNEB bill. "
            "Uses the app's spec-aware appliance model. If baseline_monthly_kwh is omitted, the user's bill-history "
            "average is used when available, else a typical 250 kWh/month home."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "changes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["add", "remove"]},
                            "category": {"type": "string", "enum": list(APPLIANCE_CATALOG.keys())},
                            "quantity": {"type": "integer", "minimum": 1},
                            "hours_per_day": {"type": "number", "minimum": 0, "maximum": 24},
                            "specs": {
                                "type": "object",
                                "description": "Optional, e.g. {capacity_ton: 1.5, star_rating: 5, inverter: true}",
                            },
                        },
                        "required": ["action", "category", "hours_per_day"],
                    },
                },
                "baseline_monthly_kwh": {"type": "number"},
            },
            "required": ["changes"],
        },
    },
    {
        "name": "estimate_bill_cost",
        "description": "TNEB slab-tariff cost (₹) for a number of units consumed over a period of days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "units_kwh": {"type": "number", "minimum": 0},
                "period_days": {"type": "integer", "minimum": 1, "maximum": 92},
            },
            "required": ["units_kwh"],
        },
    },
]


def _baseline_from_context(context: dict) -> float | None:
    bills = (context or {}).get("bill_analysis") or {}
    v = bills.get("avg_monthly_kwh")
    return float(v) if v else None


def _run_tool(name: str, args: dict, model: ApplianceModel, context: dict) -> dict:
    if name == "estimate_bill_cost":
        days = int(args.get("period_days") or 30)
        units = float(args["units_kwh"])
        return {"units_kwh": units, "period_days": days, "cost_inr": estimate_cost(units, days)}
    if name == "estimate_appliance_change":
        changes = [
            ApplianceChange(
                action=c["action"],
                category=c["category"],
                quantity=int(c.get("quantity") or 1),
                hours_per_day=float(c.get("hours_per_day", 4)),
                specs=c.get("specs") or {},
            )
            for c in args["changes"]
        ]
        baseline = args.get("baseline_monthly_kwh") or _baseline_from_context(context) or DEFAULT_BASELINE_KWH
        r = simulate(changes, model, baseline_monthly_kwh=float(baseline))
        return {
            "baseline_monthly_kwh": r.baseline_monthly_kwh,
            "new_monthly_kwh": r.new_monthly_kwh,
            "baseline_monthly_cost_inr": r.baseline_monthly_cost,
            "new_monthly_cost_inr": r.new_monthly_cost,
            "delta_monthly_cost_inr": r.delta_monthly_cost,
            "per_change": [
                {"label": c.label, "action": c.action, "qty": c.quantity, "monthly_kwh": c.monthly_kwh}
                for c in r.changes
            ],
            "tips": r.tips,
        }
    raise ValueError(f"unknown tool {name}")


def _context_block(context: dict) -> str:
    if not context:
        return "No personal data shared yet (the user hasn't uploaded bills or run a plan this session)."
    return "The user's current data in the app (JSON):\n" + json.dumps(context, default=str)[:6000]


def _chat_claude(client, messages: list[dict], context: dict, model: ApplianceModel) -> dict:
    convo: list[Any] = [{"role": m["role"], "content": m["content"]} for m in messages]
    system = [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": _context_block(context)},
    ]
    used_tools: list[str] = []
    for _ in range(MAX_TOOL_ROUNDS + 1):
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            system=system,
            tools=TOOLS,
            messages=convo,
            output_config={"effort": "low"},
            extra_headers=FALLBACK_HEADERS,
            extra_body=FALLBACK_BODY,
        )
        if response.stop_reason == "refusal":
            return {"reply": "Sorry, I can't help with that one. Ask me about your bills, appliances or saving energy!", "engine": "claude", "tools_used": used_tools}
        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text").strip()
            return {"reply": text or "…", "engine": "claude", "tools_used": used_tools}

        convo.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            used_tools.append(block.name)
            try:
                out = _run_tool(block.name, dict(block.input), model, context)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out)})
            except Exception as exc:
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True})
        convo.append({"role": "user", "content": results})

    return {"reply": "That took more steps than expected — could you narrow the question down?", "engine": "claude", "tools_used": used_tools}


# --------------------------------------------------------------- offline engine

_ALIASES = {
    "air_conditioner": ["air conditioner", "aircon", "a/c", " ac", "ac "],
    "fan": ["fan"],
    "television": ["television", "tv"],
    "lighting": ["light", "bulb", "tube"],
    "refrigerator": ["fridge", "refrigerator"],
    "washing_machine": ["washing machine", "washer"],
    "computer": ["computer", "laptop", "pc", "desktop"],
    "microwave": ["microwave", "oven"],
    "water_heater": ["geyser", "water heater", "heater"],
    "motor_pump": ["motor", "pump"],
}
_WORD_NUM = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "another": 1, "second": 1, "extra": 1}


def _find_appliances(text: str) -> list[str]:
    t = f" {text.lower()} "
    found = []
    for cat, words in _ALIASES.items():
        if any(w in t for w in words):
            found.append(cat)
    return found


def _offline_reply(messages: list[dict], context: dict, model: ApplianceModel) -> str:
    q = messages[-1]["content"].strip()
    ql = q.lower()
    bills = (context or {}).get("bill_analysis") or {}

    if re.search(r"\b(hi|hello|hey|vanakkam)\b", ql) and len(ql) < 25:
        return ("Hi! I'm Volt ⚡ — ask me things like \"What if I add a 1.5 ton AC for 6 hours?\", "
                "\"How much will 320 units cost?\" or \"How do I upload my bill?\"")

    if any(w in ql for w in ("upload", "ocr", "scan", "photo", "pdf", "handwritten")):
        return ("Open **Bill Insights** (/bills) and drop in your past bills — PDFs, phone photos or even a handwritten "
                "list like \"Jan 2025 – 245 units\". I read the units and amounts, you check them in the table, "
                "then hit Analyse for the trend, unusual months, a 3-month forecast and saving tips.")

    units_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:units?|kwh)", ql)
    appliances = _find_appliances(ql)

    if appliances and any(w in ql for w in ("add", "buy", "new", "install", "remove", "replace", "sell", "stop", "what if", "extra", "another")):
        action = "remove" if any(w in ql for w in ("remove", "sell", "stop", "get rid", "without")) else "add"
        hours_m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h|hr|hrs|hours?)\b", ql)
        # Strip spec numbers ("1.5 ton", "5 star", "8 hours") so they aren't read as a quantity.
        ql_qty = re.sub(r"\d+(?:\.\d+)?\s*(?:ton|star|h|hrs?|hours?|units?|kwh|kg|l|lit(?:re|er)s?|inch(?:es)?)\b", " ", ql)
        qty_m = re.search(r"\b(\d+|a|an|one|two|three|four|another|second|extra)\s+(?:more\s+)?(?:[\w-]+\s+){0,4}?(?:" +
                          "|".join(w.strip() for c in appliances for w in _ALIASES[c]) + ")", ql_qty)
        qty = 1
        if qty_m:
            tok = qty_m.group(1)
            qty = int(tok) if tok.isdigit() and int(tok) < 10 else _WORD_NUM.get(tok, 1)
        ton_m = re.search(r"(\d(?:\.\d)?)\s*ton", ql)
        star_m = re.search(r"(\d)\s*star", ql)
        changes = []
        for cat in appliances:
            default_h = {"refrigerator": 24, "lighting": 6, "water_heater": 0.5, "motor_pump": 0.5, "microwave": 0.3, "washing_machine": 1}.get(cat, 6)
            specs = {}
            if cat == "air_conditioner":
                specs = {"capacity_ton": float(ton_m.group(1)) if ton_m else 1.5,
                         "star_rating": int(star_m.group(1)) if star_m else 3,
                         "inverter": "inverter" in ql and "non" not in ql}
            changes.append(ApplianceChange(action, cat, qty, float(hours_m.group(1)) if hours_m else default_h, specs))
        base = _baseline_from_context(context) or DEFAULT_BASELINE_KWH
        r = simulate(changes, model, baseline_monthly_kwh=base)
        parts = ", ".join(f"{c.quantity}× {c.label} ({c.hours_per_day:g} h/day): {c.monthly_kwh:+.0f} kWh/month" for c in r.changes)
        src = "your bill-history average" if _baseline_from_context(context) else "a typical 250 kWh/month home"
        out = (f"{parts}. Starting from {src} ({r.baseline_monthly_kwh:.0f} kWh ≈ ₹{r.baseline_monthly_cost:.0f}), "
               f"you'd be at {r.new_monthly_kwh:.0f} kWh ≈ ₹{r.new_monthly_cost:.0f}/month — {r.verdict.lower()}")
        if r.tips:
            out += " Tip: " + r.tips[0]
        return out + " Try the Appliance What-If page for a detailed breakdown."

    if units_match and any(w in ql for w in ("cost", "bill", "pay", "how much", "price", "charge")):
        units = float(units_match.group(1))
        days = 60 if any(w in ql for w in ("bi-month", "bimonth", "two month", "2 month")) else 30
        return (f"{units:g} units over {days} days comes to about ₹{estimate_cost(units, days):.0f} on the TNEB "
                f"domestic slabs (planning estimate; fixed charges and fuel adjustments aren't included).")

    if any(w in ql for w in ("tariff", "slab", "rate", "per unit")):
        lines = "; ".join(
            f"{'above 400' if t == float('inf') else f'up to {int(t)}'} units ₹{r:.2f}" for t, r in settings.tariff_slabs
        )
        return (f"WattWise uses the TNEB domestic LT-IA telescopic slabs (monthly-equivalent): {lines}. "
                "Each slab only applies to the units inside it, and TNEB bills bi-monthly so the thresholds double on the bill.")

    if bills and any(w in ql for w in ("forecast", "next month", "predict", "trend", "my bill", "my usage", "coming")):
        f = (bills.get("forecast") or [{}])[0]
        return (f"Your bills show usage {bills.get('trend_direction', 'stable')} "
                f"({bills.get('trend_pct_per_month', 0):+.1f}%/month after removing seasonal swings), averaging "
                f"{bills.get('avg_monthly_kwh', 0):.0f} kWh/month. Next month looks like ~{f.get('kwh', 0):.0f} kWh "
                f"(≈ ₹{f.get('estimated_cost', 0):.0f}).")

    if any(w in ql for w in ("save", "reduce", "tip", "lower", "cut", "advice", "optimal", "optimise", "optimize")):
        return ("Biggest wins in a Tamil Nadu home: (1) AC at 24–26 °C with a ceiling fan — each degree cooler adds ~6%; "
                "(2) BLDC fans (35 W vs 75 W); (3) geyser on a 15-minute timer; (4) switch TVs/set-top boxes off at the plug; "
                "(5) keep the fridge 10 cm off the wall and its door seal tight. Upload your bills on Bill Insights for advice tuned to your own usage.")

    if any(w in ql for w in ("forecast", "predict", "model", "accuracy", "lightgbm", "machine learning", "ml", "how does")):
        return ("Two ML layers: a LightGBM day-ahead household forecaster (lag/rolling features, ~23% WMAPE on held-out REFIT data), "
                "and for uploaded bills a small-sample model tournament — naive, seasonal-naive, damped Holt smoothing and ridge "
                "regression compete on a rolling backtest of your own history and the most accurate one forecasts your next 3 months. "
                "See the Methodology page for details.")

    return ("I can help with your electricity bills, appliance what-ifs, TNEB tariffs and saving tips. Try: "
            "\"What if I add a 5-star 1.5 ton AC for 8 hours?\", \"How much will 280 units cost?\" or \"How do I upload my bill?\"")


def chat(messages: list[dict], context: dict | None, model: ApplianceModel) -> dict:
    context = context or {}
    client = get_client()
    if client is not None:
        try:
            return _chat_claude(client, messages, context, model)
        except Exception as exc:  # fall back rather than leave the user hanging
            log.warning("Claude chat failed, using offline engine: %s", exc)
    return {"reply": _offline_reply(messages, context, model), "engine": "offline", "tools_used": []}
