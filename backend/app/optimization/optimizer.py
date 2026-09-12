"""Budget-constrained appliance-hours optimizer.

Transparent, rule-based greedy search (not RL): every recommendation can be
traced back to (a) the appliance's flexibility class, (b) its relative share
of consumption, and (c) how much reduction is still needed to meet budget.
This keeps the system explainable, which matters more for a household
decision-support tool than squeezing out marginal accuracy from a black-box
RL agent.

Algorithm
---------
1. Compute each selected appliance's projected daily energy/cost at its
   current (default) usage hours.
2. If total projected cost <= budget, no changes needed.
3. Otherwise, repeatedly reduce hours on the appliance with the highest
   (flexibility_weight * current_hours * avg_watts) score — i.e. prefer
   cutting the most flexible, highest-draw appliance first — in small steps,
   recomputing cost after each step, until the budget is met or every
   appliance has hit its configured `min_hours`.
"""
from dataclasses import dataclass, field

from app.core.config import APPLIANCE_CATALOG, FLEXIBILITY_WEIGHT, estimate_cost, settings
from app.ml.models.appliance_model import ApplianceModel

STEP_HOURS = 0.5


@dataclass
class ApplianceUsage:
    category: str
    hours_per_day: float
    specs: dict = field(default_factory=dict)


@dataclass
class ApplianceResult:
    category: str
    label: str
    original_hours: float
    recommended_hours: float
    daily_kwh: float
    reduced: bool = field(default=False)


@dataclass
class TodShiftOpportunity:
    category: str
    label: str
    daily_kwh: float
    estimated_saving: float


@dataclass
class OptimizationResult:
    appliances: list[ApplianceResult]
    projected_daily_kwh: float
    projected_total_kwh: float
    projected_cost: float
    original_cost: float
    budget: float
    budget_met: bool
    duration_days: int
    tod_shift_opportunities: list[TodShiftOpportunity] = field(default_factory=list)
    tod_total_saving: float = 0.0


def _appliance_score(category: str, daily_kwh: float) -> float:
    """
    Cut-priority score: prefer trimming the most flexible appliance that is
    also currently the biggest consumer. Uses each appliance's actual
    spec-adjusted daily kWh (not nameplate wattage) so a user-specified 5-star
    inverter AC correctly scores lower than a 3-star non-inverter one at the
    same hours.
    """
    weight = FLEXIBILITY_WEIGHT[APPLIANCE_CATALOG[category]["flexibility"]]
    return weight * daily_kwh


def optimize(
    usages: list[ApplianceUsage],
    duration_days: int,
    budget: float,
    appliance_model: ApplianceModel,
    day_of_week: int = 0,
) -> OptimizationResult:
    hours = {u.category: u.hours_per_day for u in usages}
    specs_by_category = {u.category: u.specs for u in usages}
    min_hours = {c: APPLIANCE_CATALOG[c]["min_hours"] for c in hours}

    def daily_kwh_for(hours_map: dict[str, float]) -> dict[str, float]:
        return {
            c: appliance_model.estimate_kwh(c, h, day_of_week, specs_by_category.get(c))
            for c, h in hours_map.items()
        }

    original_kwh_map = daily_kwh_for(hours)
    original_daily_kwh = sum(original_kwh_map.values())
    original_cost = estimate_cost(original_daily_kwh * duration_days, duration_days)

    current_hours = dict(hours)
    current_kwh_map = dict(original_kwh_map)

    def total_cost(kwh_map: dict[str, float]) -> float:
        return estimate_cost(sum(kwh_map.values()) * duration_days, duration_days)

    guard = 0
    while total_cost(current_kwh_map) > budget and guard < 2000:
        guard += 1
        # pick the flexible appliance with the highest cut-priority score
        # among those still above their minimum hours
        candidates = [
            c for c in current_hours if current_hours[c] > min_hours[c]
        ]
        if not candidates:
            break  # can't reduce further; budget may remain unmet

        candidates.sort(
            key=lambda c: _appliance_score(c, current_kwh_map[c]), reverse=True
        )
        target = candidates[0]
        current_hours[target] = max(
            min_hours[target], current_hours[target] - STEP_HOURS
        )
        current_kwh_map = daily_kwh_for(current_hours)

    final_cost = total_cost(current_kwh_map)
    projected_daily_kwh = sum(current_kwh_map.values())

    results = [
        ApplianceResult(
            category=c,
            label=APPLIANCE_CATALOG[c]["label"],
            original_hours=hours[c],
            recommended_hours=round(current_hours[c], 2),
            daily_kwh=round(current_kwh_map[c], 3),
            reduced=current_hours[c] < hours[c],
        )
        for c in hours
    ]

    tod_opportunities, tod_total = _estimate_tod_shift_savings(
        current_hours, current_kwh_map, final_cost, projected_daily_kwh * duration_days
    )

    return OptimizationResult(
        appliances=results,
        projected_daily_kwh=round(projected_daily_kwh, 3),
        projected_total_kwh=round(projected_daily_kwh * duration_days, 3),
        projected_cost=final_cost,
        original_cost=original_cost,
        budget=budget,
        budget_met=final_cost <= budget,
        duration_days=duration_days,
        tod_shift_opportunities=tod_opportunities,
        tod_total_saving=round(tod_total, 2),
    )


def _estimate_tod_shift_savings(
    current_hours: dict[str, float],
    current_kwh_map: dict[str, float],
    total_period_cost: float,
    total_period_kwh: float,
) -> tuple[list[TodShiftOpportunity], float]:
    """
    Illustrative savings if TNEB offered time-of-day pricing (it doesn't
    today — see Settings.tod_peak_multiplier's docstring) and shiftable
    appliances (washing machine, water heater, motor pump) currently
    assumed to run during the evening peak window were moved to off-peak
    hours instead. Uses the average per-kWh rate implied by the slab tariff
    over the full period (total_period_cost / total_period_kwh) as the
    reference rate for both windows — NOT total cost divided by a single
    day's kWh, which would inflate the rate by ~duration_days times.

    `current_kwh_map` holds each appliance's DAILY kwh, so the returned
    per-appliance savings (and `total_saving`) are also daily figures —
    callers multiply by duration_days for a period total.
    """
    if total_period_kwh <= 0:
        return [], 0.0

    avg_rate = total_period_cost / total_period_kwh
    peak_cost_per_kwh = avg_rate * settings.tod_peak_multiplier
    offpeak_cost_per_kwh = avg_rate * settings.tod_offpeak_multiplier

    opportunities = []
    total_saving = 0.0
    for category, hrs in current_hours.items():
        if hrs <= 0 or not APPLIANCE_CATALOG[category].get("shiftable"):
            continue
        daily_kwh = current_kwh_map[category]
        saving = daily_kwh * (peak_cost_per_kwh - offpeak_cost_per_kwh)
        if saving <= 0:
            continue
        opportunities.append(
            TodShiftOpportunity(
                category=category,
                label=APPLIANCE_CATALOG[category]["label"],
                daily_kwh=round(daily_kwh, 3),
                estimated_saving=round(saving, 2),
            )
        )
        total_saving += saving

    return opportunities, total_saving
