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

from app.core.config import APPLIANCE_CATALOG, FLEXIBILITY_WEIGHT, estimate_cost
from app.ml.models.appliance_model import ApplianceModel

STEP_HOURS = 0.5


@dataclass
class ApplianceUsage:
    category: str
    hours_per_day: float


@dataclass
class ApplianceResult:
    category: str
    label: str
    original_hours: float
    recommended_hours: float
    daily_kwh: float
    reduced: bool = field(default=False)


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


def _appliance_score(category: str, hours: float) -> float:
    catalog = APPLIANCE_CATALOG[category]
    weight = FLEXIBILITY_WEIGHT[catalog["flexibility"]]
    return weight * hours * catalog["avg_watts"]


def optimize(
    usages: list[ApplianceUsage],
    duration_days: int,
    budget: float,
    appliance_model: ApplianceModel,
    day_of_week: int = 0,
) -> OptimizationResult:
    hours = {u.category: u.hours_per_day for u in usages}
    min_hours = {c: APPLIANCE_CATALOG[c]["min_hours"] for c in hours}

    def daily_kwh_for(hours_map: dict[str, float]) -> dict[str, float]:
        return {
            c: appliance_model.estimate_kwh(c, h, day_of_week)
            for c, h in hours_map.items()
        }

    original_kwh_map = daily_kwh_for(hours)
    original_daily_kwh = sum(original_kwh_map.values())
    original_cost = estimate_cost(original_daily_kwh * duration_days)

    current_hours = dict(hours)
    current_kwh_map = dict(original_kwh_map)

    def total_cost(kwh_map: dict[str, float]) -> float:
        return estimate_cost(sum(kwh_map.values()) * duration_days)

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
            key=lambda c: _appliance_score(c, current_hours[c]), reverse=True
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

    return OptimizationResult(
        appliances=results,
        projected_daily_kwh=round(projected_daily_kwh, 3),
        projected_total_kwh=round(projected_daily_kwh * duration_days, 3),
        projected_cost=final_cost,
        original_cost=original_cost,
        budget=budget,
        budget_met=final_cost <= budget,
        duration_days=duration_days,
    )
