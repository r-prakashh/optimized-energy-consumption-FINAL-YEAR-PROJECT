"""Per-appliance specification schema and spec-driven wattage estimation.

Rather than one flat wattage per appliance category, this lets a user
describe the actual model they own — AC tonnage and BEE star rating,
refrigerator capacity, washing machine type, etc. — and computes an
effective wattage from that, closer to what a real energy audit would use.

BEE (Bureau of Energy Efficiency) star ratings are India's standard
appliance efficiency labels; the multipliers below are approximate typical
ranges for planning purposes, not certified BEE test figures for a specific
model — a real product would pull the exact label data per model number.
"""
from dataclasses import dataclass, field
from typing import Any, Literal

FieldType = Literal["select", "boolean"]


@dataclass
class SpecField:
    key: str
    label: str
    type: FieldType
    options: list[Any] = field(default_factory=list)
    default: Any = None
    unit: str = ""


# BEE star rating -> relative efficiency multiplier vs a 3-star baseline.
# Each additional star is roughly a 8-10% efficiency gain in practice.
STAR_RATING_MULTIPLIER = {3: 1.0, 4: 0.90, 5: 0.80}

APPLIANCE_SPECS: dict[str, list[SpecField]] = {
    "air_conditioner": [
        SpecField("capacity_ton", "Capacity", "select", [1.0, 1.5, 2.0], 1.5, "Ton"),
        SpecField("star_rating", "BEE Star Rating", "select", [3, 4, 5], 3, "Star"),
        SpecField("inverter", "Inverter compressor", "boolean", [], True),
    ],
    "refrigerator": [
        SpecField("capacity_liters", "Capacity", "select", [190, 250, 340, 450], 250, "L"),
        SpecField("star_rating", "BEE Star Rating", "select", [3, 4, 5], 3, "Star"),
    ],
    "washing_machine": [
        SpecField("capacity_kg", "Capacity", "select", [6, 7, 8], 7, "kg"),
        SpecField("load_type", "Type", "select", ["top_load", "front_load"], "top_load"),
    ],
    "water_heater": [
        SpecField("capacity_liters", "Capacity", "select", [10, 15, 25], 15, "L"),
    ],
    "fan": [
        SpecField("motor_type", "Motor type", "select", ["standard", "bldc_5star"], "standard"),
    ],
    "television": [
        SpecField("screen_size_inches", "Screen size", "select", [32, 43, 55], 32, "in"),
    ],
}


def get_specs_schema() -> dict[str, list[dict]]:
    """JSON-friendly version of APPLIANCE_SPECS for the /appliances endpoint."""
    return {
        category: [
            {
                "key": f.key,
                "label": f.label,
                "type": f.type,
                "options": f.options,
                "default": f.default,
                "unit": f.unit,
            }
            for f in fields
        ]
        for category, fields in APPLIANCE_SPECS.items()
    }


def compute_effective_watts(category: str, base_watts: float, specs: dict[str, Any]) -> float:
    """
    Adjusts a category's baseline wattage using user-supplied specs. Falls
    back to `base_watts` unchanged for categories with no spec model, or
    when `specs` is empty (keeps the system fully usable without filling in
    every field).
    """
    if not specs:
        return base_watts

    if category == "air_conditioner":
        capacity_ton = float(specs.get("capacity_ton", 1.5))
        star = int(specs.get("star_rating", 3))
        inverter = bool(specs.get("inverter", True))
        watts_per_ton = 1200.0  # typical input power per ton, 3-star non-inverter baseline
        watts = watts_per_ton * capacity_ton * STAR_RATING_MULTIPLIER.get(star, 1.0)
        if inverter:
            watts *= 0.85  # inverter compressors modulate load instead of on/off cycling
        return watts

    if category == "refrigerator":
        capacity_liters = float(specs.get("capacity_liters", 250))
        star = int(specs.get("star_rating", 3))
        watts = 0.5 * capacity_liters * STAR_RATING_MULTIPLIER.get(star, 1.0)
        return watts

    if category == "washing_machine":
        capacity_kg = float(specs.get("capacity_kg", 7))
        load_type = specs.get("load_type", "top_load")
        watts = 400 + 20 * capacity_kg
        if load_type == "front_load":
            watts *= 0.9  # front-loaders typically run more efficient wash cycles
        return watts

    if category == "water_heater":
        capacity_liters = float(specs.get("capacity_liters", 15))
        # Heating element wattage scales mildly with tank size (not linearly —
        # usage duration, driven by the user's own hours input, matters more).
        return 1500 + 15 * capacity_liters

    if category == "fan":
        motor_type = specs.get("motor_type", "standard")
        return 35.0 if motor_type == "bldc_5star" else base_watts

    if category == "television":
        screen_size = float(specs.get("screen_size_inches", 32))
        return 1.5 * screen_size + 30

    return base_watts
