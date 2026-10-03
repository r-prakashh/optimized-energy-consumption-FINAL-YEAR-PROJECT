"""Appliance add/remove scenario simulator.

Answers "what happens to my bill if I buy a second AC / replace my geyser /
stop using the old fridge?". Each change is costed with the same
spec-aware `ApplianceModel.estimate_kwh` the planner uses (including the
live-weather AC multiplier), then layered onto a baseline:

* the household's bill-derived forecast, when bills were uploaded — so the
  answer is "your expected May bill goes from X to Y", grounded in the
  resident's own history; or
* a plain monthly kWh figure the user types in.

Cost is always recomputed through the TNEB slab tariff on the *new total*,
not by multiplying the delta by a flat rate — adding 60 units can cost far
more than 60 x average rate when it pushes the home into a higher slab.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import APPLIANCE_CATALOG, estimate_cost
from app.ml.models.appliance_model import ApplianceModel

DAYS_PER_MONTH = 30.4
WEEK = range(7)


@dataclass
class ApplianceChange:
    action: str                   # "add" | "remove"
    category: str
    quantity: int = 1
    hours_per_day: float = 4.0
    specs: dict = field(default_factory=dict)


@dataclass
class ChangeImpact:
    action: str
    category: str
    label: str
    quantity: int
    hours_per_day: float
    daily_kwh: float              # signed: + for add, - for remove
    monthly_kwh: float


@dataclass
class MonthImpact:
    label: str
    baseline_kwh: float
    new_kwh: float
    baseline_cost: float
    new_cost: float


@dataclass
class ScenarioResult:
    baseline_monthly_kwh: float
    new_monthly_kwh: float
    baseline_monthly_cost: float
    new_monthly_cost: float
    delta_monthly_kwh: float
    delta_monthly_cost: float
    delta_pct: float
    changes: list[ChangeImpact]
    months: list[MonthImpact]
    verdict: str
    tips: list[str]


def _avg_daily_kwh(model: ApplianceModel, change: ApplianceChange) -> float:
    """Average over a week so weekday/weekend duty-cycle effects net out."""
    per_day = [
        model.estimate_kwh(change.category, change.hours_per_day, d, change.specs) for d in WEEK
    ]
    return sum(per_day) / len(per_day) * max(change.quantity, 1)


def simulate(
    changes: list[ApplianceChange],
    model: ApplianceModel,
    baseline_monthly_kwh: float | None = None,
    baseline_months: list[tuple[str, float]] | None = None,
) -> ScenarioResult:
    for c in changes:
        if c.category not in APPLIANCE_CATALOG:
            raise ValueError(f"Unknown appliance: {c.category}")
        if c.action not in ("add", "remove"):
            raise ValueError("action must be 'add' or 'remove'")

    impacts: list[ChangeImpact] = []
    delta_daily = 0.0
    for c in changes:
        kwh = _avg_daily_kwh(model, c)
        signed = kwh if c.action == "add" else -kwh
        delta_daily += signed
        impacts.append(
            ChangeImpact(
                action=c.action,
                category=c.category,
                label=APPLIANCE_CATALOG[c.category]["label"],
                quantity=c.quantity,
                hours_per_day=c.hours_per_day,
                daily_kwh=round(signed, 3),
                monthly_kwh=round(signed * DAYS_PER_MONTH, 1),
            )
        )
    delta_monthly = delta_daily * DAYS_PER_MONTH

    if baseline_months:
        base = sum(k for _, k in baseline_months) / len(baseline_months)
    elif baseline_monthly_kwh is not None:
        base = baseline_monthly_kwh
    else:
        raise ValueError("Provide a baseline (monthly kWh) or upload bills first.")

    new = max(base + delta_monthly, 0.0)
    base_cost = estimate_cost(base, 30)
    new_cost = estimate_cost(new, 30)

    months = [
        MonthImpact(
            label=label,
            baseline_kwh=round(k, 1),
            new_kwh=round(max(k + delta_monthly, 0.0), 1),
            baseline_cost=estimate_cost(k, 30),
            new_cost=estimate_cost(max(k + delta_monthly, 0.0), 30),
        )
        for label, k in (baseline_months or [])
    ]

    d_cost = new_cost - base_cost
    pct = 100 * (new - base) / base if base else 0.0
    if abs(d_cost) < 1:
        verdict = "These changes barely move your bill."
    elif d_cost > 0:
        verdict = f"Your bill would rise by about ₹{d_cost:.0f}/month ({pct:+.0f}% energy)."
    else:
        verdict = f"You'd save about ₹{-d_cost:.0f}/month ({pct:+.0f}% energy)."

    tips = _scenario_tips(changes, impacts, base, new)
    return ScenarioResult(
        baseline_monthly_kwh=round(base, 1),
        new_monthly_kwh=round(new, 1),
        baseline_monthly_cost=base_cost,
        new_monthly_cost=new_cost,
        delta_monthly_kwh=round(new - base, 1),
        delta_monthly_cost=round(d_cost, 2),
        delta_pct=round(pct, 1),
        changes=impacts,
        months=months,
        verdict=verdict,
        tips=tips,
    )


def _scenario_tips(changes, impacts, base, new) -> list[str]:
    from app.ml.bill_trend import slab_position

    tips = []
    b, n = slab_position(base), slab_position(new)
    if n.get("marginal_rate", 0) > b.get("marginal_rate", 0):
        tips.append(
            f"This pushes your home from the ₹{b['marginal_rate']:.2f} into the "
            f"₹{n['marginal_rate']:.2f}/kWh slab — the extra units cost more than your current average."
        )
    for c in changes:
        if c.action != "add":
            continue
        if c.category == "air_conditioner" and not (c.specs.get("inverter") and int(c.specs.get("star_rating", 3)) >= 5):
            tips.append("Choosing a 5-star inverter AC instead uses roughly 30% less energy for the same hours.")
        if c.category == "fan" and c.specs.get("motor_type") != "bldc_5star":
            tips.append("BLDC fans draw ~35 W vs ~75 W — more than half the running cost saved.")
        if c.category == "water_heater":
            tips.append("Run the geyser for 15–20 min with a timer instead of leaving it on — most of the energy goes to standing losses.")
        if c.category == "refrigerator" and int(c.specs.get("star_rating", 3)) < 5:
            tips.append("A fridge runs 24×7 for 10+ years — the 5-star model's price premium usually pays back in 2–4 years.")
    if not tips and new < base:
        tips.append("Removing or replacing appliances you rarely need is the easiest saving there is.")
    return tips
