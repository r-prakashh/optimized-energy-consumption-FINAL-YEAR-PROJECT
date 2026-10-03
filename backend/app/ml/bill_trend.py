"""Bill-history trend analysis & forecasting.

Input: a handful of past bills (typically 3-12 periods, monthly or TNEB
bi-monthly). Output: a normalised monthly series, its trend, anomalous
months, an N-month forecast with an 80% prediction interval, and cost.

Why not the LightGBM household forecaster here? That model needs a dense
daily history (lags, 30-day rolling windows); a resident uploading bills has
a few monthly points. Small-sample time-series needs small, regularised
models, so this module runs a **model-selection tournament** over candidate
forecasters and picks the one with the lowest rolling-origin backtest error
on the user's own history:

* ``naive``            — last value carried forward (the benchmark to beat)
* ``seasonal_naive``   — last value re-scaled by the Tamil Nadu cooling-season
                         index (summer months draw more AC/fan load)
* ``holt``             — Holt's linear exponential smoothing on the
                         de-seasonalised series (level + trend), smoothing
                         constants fitted by grid search
* ``ridge``            — ridge regression on [time, sin/cos(month)] features
                         (only with >= 6 points, otherwise it overfits)

Anomalies are found with a robust z-score (median/MAD) on the
de-seasonalised series, so a hot May isn't flagged just for being May.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from app.core.config import estimate_cost, settings

DAYS_PER_MONTH = 30.4

# Relative monthly consumption index for a Tamil Nadu home (mean = 1.0).
# Cooling-driven: peaks in the Apr-Jun pre-monsoon heat, dips in the
# Nov-Jan north-east monsoon / mild winter. Approximate shape from TN
# discom seasonal demand patterns — used as a prior, not a fitted parameter.
TN_SEASONAL_INDEX = {
    1: 0.86, 2: 0.90, 3: 1.02, 4: 1.17, 5: 1.25, 6: 1.12,
    7: 1.02, 8: 0.99, 9: 0.98, 10: 0.94, 11: 0.88, 12: 0.87,
}
_mean_idx = float(np.mean(list(TN_SEASONAL_INDEX.values())))
TN_SEASONAL_INDEX = {k: v / _mean_idx for k, v in TN_SEASONAL_INDEX.items()}


@dataclass
class BillReading:
    period_end: date
    period_days: int
    units_kwh: float
    amount_inr: float | None = None


@dataclass
class MonthPoint:
    label: str            # "2025-04"
    month: int
    year: int
    kwh: float            # monthly-equivalent kWh
    daily_kwh: float
    amount_inr: float | None = None
    estimated_cost: float = 0.0
    is_anomaly: bool = False
    anomaly_score: float = 0.0


@dataclass
class ForecastPoint:
    label: str
    month: int
    year: int
    kwh: float
    lower: float
    upper: float
    estimated_cost: float


@dataclass
class TrendAnalysis:
    history: list[MonthPoint]
    forecast: list[ForecastPoint]
    model_used: str
    model_scores: dict[str, float]          # backtest MAE (kWh/month) per candidate
    trend_pct_per_month: float              # de-seasonalised slope as % of mean
    trend_direction: str                    # "rising" | "falling" | "stable"
    avg_monthly_kwh: float
    avg_monthly_cost: float
    baseload_kwh_per_day: float             # always-on floor (fridge, standby...)
    peak_month: str
    low_month: str
    billing_cycle_days: int
    tariff_check: str | None = None
    notes: list[str] = field(default_factory=list)


def _month_add(year: int, month: int, k: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + k
    return idx // 12, idx % 12 + 1


def _period_mid(r: BillReading) -> date:
    return r.period_end - timedelta(days=r.period_days // 2)


def normalise_to_months(readings: list[BillReading]) -> list[MonthPoint]:
    """Each bill is spread uniformly over the calendar days it covers, then
    re-aggregated per calendar month — so a 60-day TNEB bill becomes two
    monthly points, and monthly bills map one-to-one."""
    per_month: dict[tuple[int, int], list[float]] = {}
    amounts: dict[tuple[int, int], float] = {}
    for r in sorted(readings, key=lambda x: x.period_end):
        daily = r.units_kwh / max(r.period_days, 1)
        start = r.period_end - timedelta(days=r.period_days - 1)
        for i in range(r.period_days):
            d = start + timedelta(days=i)
            per_month.setdefault((d.year, d.month), []).append(daily)
        if r.amount_inr is not None:
            key = (_period_mid(r).year, _period_mid(r).month)
            amounts[key] = amounts.get(key, 0.0) + r.amount_inr

    points = []
    for (y, m), dailies in sorted(per_month.items()):
        # Drop calendar months the bills only cover a sliver of (<10 days);
        # extrapolating a month from 3 days of data adds noise, not signal.
        if len(dailies) < 10:
            continue
        daily = float(np.mean(dailies))
        kwh = daily * DAYS_PER_MONTH
        points.append(
            MonthPoint(
                label=f"{y}-{m:02d}",
                month=m,
                year=y,
                kwh=round(kwh, 1),
                daily_kwh=round(daily, 2),
                estimated_cost=estimate_cost(kwh, 30),
            )
        )
    return points


# ---------------------------------------------------------------- forecasters

def _deseason(values: np.ndarray, months: list[int]) -> np.ndarray:
    return values / np.array([TN_SEASONAL_INDEX[m] for m in months])


def _fc_naive(y: np.ndarray, months: list[int], future_months: list[int]) -> np.ndarray:
    return np.full(len(future_months), y[-1])


def _fc_seasonal_naive(y: np.ndarray, months: list[int], future_months: list[int]) -> np.ndarray:
    level = _deseason(y, months)[-3:].mean()
    return np.array([level * TN_SEASONAL_INDEX[m] for m in future_months])


def _holt_fit(z: np.ndarray, alpha: float, beta: float) -> tuple[float, float, float]:
    level, trend = z[0], (z[1] - z[0]) if len(z) > 1 else 0.0
    sse = 0.0
    for t in range(1, len(z)):
        pred = level + trend
        sse += (z[t] - pred) ** 2
        new_level = alpha * z[t] + (1 - alpha) * (level + trend)
        trend = beta * (new_level - level) + (1 - beta) * trend
        level = new_level
    return level, trend, sse


def _fc_holt(y: np.ndarray, months: list[int], future_months: list[int]) -> np.ndarray:
    z = _deseason(y, months)
    best = None
    for alpha in (0.2, 0.4, 0.6, 0.8):
        for beta in (0.05, 0.15, 0.3):
            level, trend, sse = _holt_fit(z, alpha, beta)
            if best is None or sse < best[2]:
                best = (level, trend, sse)
    level, trend, _ = best
    # Damp the trend (phi=0.8) — undamped linear trends from 4-6 points
    # extrapolate absurdly over a few months.
    phi = 0.8
    out = []
    damp = 0.0
    for h, m in enumerate(future_months, start=1):
        damp += phi ** h
        out.append(max(level + damp * trend, 0.0) * TN_SEASONAL_INDEX[m])
    return np.array(out)


def _ridge_features(t: np.ndarray, months: list[int]) -> np.ndarray:
    ang = 2 * np.pi * (np.array(months) - 1) / 12
    return np.column_stack([np.ones_like(t, dtype=float), t, np.sin(ang), np.cos(ang)])


def _fc_ridge(y: np.ndarray, months: list[int], future_months: list[int], lam: float = 1.0) -> np.ndarray:
    t = np.arange(len(y), dtype=float)
    X = _ridge_features(t, months)
    scale = y.mean() or 1.0
    reg = lam * np.eye(X.shape[1])
    reg[0, 0] = 0.0  # don't shrink the intercept
    w = np.linalg.solve(X.T @ X + reg, X.T @ (y / scale))
    tf = np.arange(len(y), len(y) + len(future_months), dtype=float)
    return np.maximum(_ridge_features(tf, future_months) @ w * scale, 0.0)


FORECASTERS = {
    "naive": (_fc_naive, 1),
    "seasonal_naive": (_fc_seasonal_naive, 1),
    "holt": (_fc_holt, 3),
    "ridge": (_fc_ridge, 6),
}


def _backtest(y: np.ndarray, months: list[int]) -> dict[str, float]:
    """Rolling-origin one-step-ahead MAE for each eligible candidate."""
    scores: dict[str, float] = {}
    for name, (fn, min_n) in FORECASTERS.items():
        errors = []
        for cut in range(max(min_n, 2), len(y)):
            pred = fn(y[:cut], months[:cut], [months[cut]])[0]
            errors.append(abs(pred - y[cut]))
        if errors:
            scores[name] = round(float(np.mean(errors)), 2)
    return scores


def _robust_anomalies(y: np.ndarray, months: list[int]) -> np.ndarray:
    z = _deseason(y, months)
    if len(z) < 4:
        return np.zeros(len(z))
    med = np.median(z)
    mad = np.median(np.abs(z - med)) or (np.std(z) or 1.0) / 1.4826
    return 0.6745 * (z - med) / mad


# ------------------------------------------------------------------ analysis

def analyse(readings: list[BillReading], horizon_months: int = 3) -> TrendAnalysis:
    if not readings:
        raise ValueError("Add at least one bill to analyse.")

    history = normalise_to_months(readings)
    if not history:
        raise ValueError("The bills don't cover enough days to form a monthly picture.")

    y = np.array([p.kwh for p in history], dtype=float)
    months = [p.month for p in history]

    # Attach actual billed amounts back to the month they were centred on.
    by_label = {p.label: p for p in history}
    for r in readings:
        if r.amount_inr is not None:
            mid = _period_mid(r)
            p = by_label.get(f"{mid.year}-{mid.month:02d}")
            if p:
                p.amount_inr = round(r.amount_inr, 2)

    # Anomalies
    zscores = _robust_anomalies(y, months)
    for p, z in zip(history, zscores):
        p.anomaly_score = round(float(z), 2)
        p.is_anomaly = bool(abs(z) > 2.5)

    # Model tournament
    scores = _backtest(y, months)
    eligible = [n for n, (_, min_n) in FORECASTERS.items() if len(y) >= min_n]
    if scores:
        model_used = min(scores, key=scores.get)
    else:
        model_used = "seasonal_naive" if "seasonal_naive" in eligible else "naive"

    last = history[-1]
    future = [_month_add(last.year, last.month, k) for k in range(1, horizon_months + 1)]
    future_months = [m for _, m in future]
    fn = FORECASTERS[model_used][0]
    # Anomalous months are down-weighted out of the fit by replacing them
    # with their seasonal expectation, so one AC-heavy guest month doesn't
    # bend the forecast.
    y_fit = y.copy()
    z = _deseason(y, months)
    for i, p in enumerate(history):
        if p.is_anomaly:
            y_fit[i] = np.median(z) * TN_SEASONAL_INDEX[p.month]
    preds = fn(y_fit, months, future_months)

    resid_sd = scores.get(model_used) if scores else None
    if not resid_sd:
        resid_sd = 0.12 * float(np.mean(y))  # 12% default uncertainty with no backtest
    forecast = []
    for h, ((yy, mm), pred) in enumerate(zip(future, preds), start=1):
        band = 1.28 * resid_sd * 1.25 * np.sqrt(h)  # MAE*1.25 ~ sd; 1.28 -> 80% interval
        forecast.append(
            ForecastPoint(
                label=f"{yy}-{mm:02d}",
                month=mm,
                year=yy,
                kwh=round(float(pred), 1),
                lower=round(max(float(pred - band), 0.0), 1),
                upper=round(float(pred + band), 1),
                estimated_cost=estimate_cost(float(pred), 30),
            )
        )

    # Trend: slope of de-seasonalised series, as % of mean per month
    if len(z) >= 2:
        slope = float(np.polyfit(np.arange(len(z)), z, 1)[0])
        trend_pct = 100 * slope / float(np.mean(z))
    else:
        trend_pct = 0.0
    direction = "rising" if trend_pct > 2 else "falling" if trend_pct < -2 else "stable"

    cycle = int(round(np.median([r.period_days for r in readings])))

    tariff_check = None
    billed = [r for r in readings if r.amount_inr]
    if billed:
        est = sum(estimate_cost(r.units_kwh, r.period_days) for r in billed)
        act = sum(r.amount_inr for r in billed)
        diff_pct = 100 * (act - est) / est if est else 0
        if abs(diff_pct) <= 15:
            tariff_check = f"Your billed amounts match the TNEB tariff estimate within {abs(diff_pct):.0f}%."
        else:
            more_less = "higher" if diff_pct > 0 else "lower"
            tariff_check = (
                f"Your billed amounts are {abs(diff_pct):.0f}% {more_less} than the TNEB slab estimate — "
                "this can be fixed charges, arrears, a different tariff category, or a misread value."
            )

    peak = max(history, key=lambda p: p.kwh)
    low = min(history, key=lambda p: p.kwh)
    notes = []
    if len(history) < 4:
        notes.append("Fewer than 4 months of history — forecasts lean on the Tamil Nadu seasonal prior. Add more bills for a personalised model.")

    return TrendAnalysis(
        history=history,
        forecast=forecast,
        model_used=model_used,
        model_scores=scores,
        trend_pct_per_month=round(trend_pct, 2),
        trend_direction=direction,
        avg_monthly_kwh=round(float(np.mean(y)), 1),
        avg_monthly_cost=round(float(np.mean([p.estimated_cost for p in history])), 2),
        baseload_kwh_per_day=round(min(p.daily_kwh for p in history) * 0.55, 2),
        peak_month=peak.label,
        low_month=low.label,
        billing_cycle_days=cycle,
        tariff_check=tariff_check,
        notes=notes,
    )


# ------------------------------------------------------------------- advice

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _pretty(label: str) -> str:
    y, m = label.split("-")
    return f"{MONTH_NAMES[int(m) - 1]} {y}"


def slab_position(monthly_kwh: float) -> dict:
    """Where a monthly consumption sits in the TNEB slab ladder."""
    prev = 0.0
    for threshold, rate in settings.tariff_slabs:
        if monthly_kwh <= threshold:
            return {
                "slab_floor": prev,
                "slab_ceiling": None if threshold == float("inf") else threshold,
                "marginal_rate": rate,
                "headroom_kwh": None if threshold == float("inf") else round(threshold - monthly_kwh, 1),
                "over_previous_kwh": round(monthly_kwh - prev, 1),
            }
        prev = threshold
    return {}


def optimal_target(monthly_kwh: float) -> dict:
    """Recommends a monthly kWh target: drop to the slab boundary below if
    that needs <= 20% cut, otherwise a 10% efficiency target."""
    pos = slab_position(monthly_kwh)
    floor = pos.get("slab_floor", 0.0)
    if floor > 0 and (monthly_kwh - floor) / monthly_kwh <= 0.20:
        target = floor
        reason = f"Staying at or under {floor:.0f} units/month keeps every unit out of the ₹{pos['marginal_rate']:.2f} slab."
    else:
        target = round(monthly_kwh * 0.9, 1)
        reason = "A realistic 10% efficiency target (thermostat, standby and scheduling changes)."
    saving = estimate_cost(monthly_kwh, 30) - estimate_cost(target, 30)
    return {
        "target_monthly_kwh": round(target, 1),
        "target_daily_kwh": round(target / DAYS_PER_MONTH, 2),
        "current_monthly_kwh": round(monthly_kwh, 1),
        "monthly_saving_inr": round(saving, 2),
        "reason": reason,
    }


def generate_advice(a: TrendAnalysis) -> list[dict]:
    """Plain-language advice cards: {kind, title, body}."""
    tips: list[dict] = []
    nxt = a.forecast[0] if a.forecast else None

    if a.trend_direction == "rising":
        tips.append({
            "kind": "warn",
            "title": f"Usage is rising ~{a.trend_pct_per_month:.1f}% a month",
            "body": "After removing normal seasonal swings, your consumption is still climbing. "
                    "A new appliance, longer AC hours or an ageing fridge/AC compressor are the usual causes.",
        })
    elif a.trend_direction == "falling":
        tips.append({
            "kind": "ok",
            "title": f"Nice — usage is falling ~{abs(a.trend_pct_per_month):.1f}% a month",
            "body": "Your season-adjusted consumption is trending down. Keep the habits that got you here.",
        })
    else:
        tips.append({
            "kind": "info",
            "title": "Usage is steady",
            "body": "Season-adjusted consumption is flat — month-to-month changes are mostly weather.",
        })

    for p in a.history:
        if p.is_anomaly:
            direction = "above" if p.anomaly_score > 0 else "below"
            tips.append({
                "kind": "warn" if p.anomaly_score > 0 else "info",
                "title": f"{_pretty(p.label)} was unusually {'high' if p.anomaly_score > 0 else 'low'}",
                "body": f"{p.kwh:.0f} kWh is well {direction} what the season explains. "
                        + ("Check for guests, a stuck geyser thermostat, a leaking pump or a faulty appliance."
                           if p.anomaly_score > 0 else "Travel or a meter-reading estimate can cause this."),
            })

    if nxt:
        pos = slab_position(nxt.kwh)
        tips.append({
            "kind": "info",
            "title": f"Next month ({_pretty(nxt.label)}): ~{nxt.kwh:.0f} kWh, ≈ ₹{nxt.estimated_cost:.0f}",
            "body": f"Likely range {nxt.lower:.0f}–{nxt.upper:.0f} kWh. Your last units fall in the "
                    f"₹{pos.get('marginal_rate', 0):.2f}/kWh slab.",
        })
        if pos.get("headroom_kwh") is not None and 0 < (nxt.kwh - pos["slab_floor"]) <= 40 and pos["slab_floor"] > 0:
            tips.append({
                "kind": "warn",
                "title": f"Just {nxt.kwh - pos['slab_floor']:.0f} units into a higher slab",
                "body": f"Cutting about {(nxt.kwh - pos['slab_floor']) / DAYS_PER_MONTH:.1f} kWh/day "
                        f"(≈ {((nxt.kwh - pos['slab_floor']) / DAYS_PER_MONTH) / 1.2:.1f} h less of a 1.5-ton AC) "
                        f"keeps you under {pos['slab_floor']:.0f} units.",
            })
        if nxt.month in (3, 4, 5, 6):
            tips.append({
                "kind": "info",
                "title": "Summer peak ahead",
                "body": "Set the AC to 24–26 °C (each degree lower adds ~6% energy), use ceiling fans with the AC, "
                        "and close curtains on west-facing windows in the afternoon.",
            })
        elif nxt.month in (11, 12, 1):
            tips.append({
                "kind": "ok",
                "title": "Cool season — a chance to bank savings",
                "body": "AC load is naturally low now. Use the slack to run the geyser for shorter cycles "
                        "(10–15 min is enough with an insulated tank).",
            })

    if a.baseload_kwh_per_day > 2.5:
        tips.append({
            "kind": "info",
            "title": f"Always-on load ≈ {a.baseload_kwh_per_day:.1f} kWh/day",
            "body": "That's the floor your home never goes below — fridge, Wi-Fi, standby TVs/set-top boxes. "
                    "Switching off standby at the plug typically trims 0.3–0.6 kWh/day.",
        })

    if a.tariff_check:
        tips.append({"kind": "info", "title": "Bill check", "body": a.tariff_check})

    return tips
