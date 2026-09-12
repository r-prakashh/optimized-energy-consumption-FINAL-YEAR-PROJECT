"""Turns the optimizer's numeric output into plain-language, per-appliance
recommendations — the "so what should I actually do" layer on top of the
hours/kWh/cost numbers, using the specs the user entered where relevant.
"""
from app.core.appliance_specs import compute_effective_watts
from app.core.config import APPLIANCE_CATALOG
from app.optimization.optimizer import OptimizationResult


def _spec_summary(category: str, specs: dict) -> str:
    if not specs:
        return ""
    if category == "air_conditioner":
        ton = specs.get("capacity_ton")
        star = specs.get("star_rating")
        inverter = "inverter" if specs.get("inverter") else "non-inverter"
        return f" ({ton} Ton, {star}-star, {inverter})" if ton and star else ""
    if category == "refrigerator":
        liters = specs.get("capacity_liters")
        star = specs.get("star_rating")
        return f" ({liters} L, {star}-star)" if liters and star else ""
    if category == "washing_machine":
        kg = specs.get("capacity_kg")
        load = specs.get("load_type", "").replace("_", "-")
        return f" ({kg} kg, {load})" if kg else ""
    if category == "water_heater":
        liters = specs.get("capacity_liters")
        return f" ({liters} L)" if liters else ""
    if category == "television":
        size = specs.get("screen_size_inches")
        return f" ({size}-inch)" if size else ""
    return ""


def _upgrade_tip(category: str, specs: dict) -> str | None:
    """
    Suggests a concrete efficiency upgrade when the current spec isn't
    already the most efficient option, quantifying the saving by calling
    the SAME `compute_effective_watts` function the estimator itself uses
    for current vs. best-case specs — so the percentage is internally
    consistent by construction, not a separately hand-tuned number.
    """
    if not specs or category not in APPLIANCE_CATALOG:
        return None

    base_watts = APPLIANCE_CATALOG[category]["avg_watts"]
    current_watts = compute_effective_watts(category, base_watts, specs)

    best_specs = dict(specs)
    if category in ("air_conditioner", "refrigerator"):
        if specs.get("star_rating", 3) >= 5 and specs.get("inverter", True):
            return None
        best_specs["star_rating"] = 5
        best_specs["inverter"] = True
        label = "a 5-star inverter model" if category == "air_conditioner" else "a 5-star model"
    elif category == "fan":
        if specs.get("motor_type") == "bldc_5star":
            return None
        best_specs["motor_type"] = "bldc_5star"
        label = "a BLDC 5-star fan"
    else:
        return None

    best_watts = compute_effective_watts(category, base_watts, best_specs)
    if best_watts >= current_watts:
        return None
    savings_pct = round((1 - best_watts / current_watts) * 100)
    return f"Upgrading to {label} would cut this appliance's energy use by roughly {savings_pct}% at the same hours."


def generate_action_plan(
    result: OptimizationResult, specs_by_category: dict[str, dict]
) -> list[str]:
    lines: list[str] = []
    tod_by_category = {o.category: o for o in result.tod_shift_opportunities}

    for a in result.appliances:
        specs = specs_by_category.get(a.category, {})
        name = a.label + _spec_summary(a.category, specs)

        if a.reduced:
            saved_hours = round(a.original_hours - a.recommended_hours, 2)
            lines.append(
                f"Cut {name} from {a.original_hours}h to {a.recommended_hours}h/day "
                f"({saved_hours}h less) to help stay within budget."
            )
        elif a.category == "refrigerator":
            lines.append(f"{name} runs continuously as expected — no change needed for an essential load.")
        else:
            lines.append(f"Keep {name} at {a.recommended_hours}h/day — it already fits your budget.")

        tip = _upgrade_tip(a.category, specs)
        if tip:
            lines.append(f"  → {tip}")

        shift = tod_by_category.get(a.category)
        if shift:
            lines.append(
                f"  → {name} runs unattended — shifting it to off-peak hours (11pm-6am) could "
                f"save an estimated ₹{shift.estimated_saving * result.duration_days:.2f} over "
                f"{result.duration_days} days if your utility offered time-of-day pricing."
            )

    if not result.budget_met:
        lines.append(
            "Even at minimum hours for essential appliances, the projected cost still "
            "exceeds your budget — consider raising the budget or removing a high-consumption appliance."
        )

    return lines
