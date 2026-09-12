"""Central configuration: tariff slabs and the appliance catalog.

Appliance wattages are typical nameplate/approximate ratings (documented in the
project report) used as the physics-based baseline; REFIT-derived duty-cycle
models (see app/ml/models/appliance_model.py) refine these into realistic
energy-per-hour-used figures per appliance category.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


# Generic appliance categories the system supports. `refit_channel_key` maps
# to the label used in REFIT's per-house appliance channel metadata so the
# training pipeline can pool same-category appliances across houses.
APPLIANCE_CATALOG = {
    "air_conditioner": {
        "label": "Air Conditioner",
        "avg_watts": 1500,
        "flexibility": "high",       # can be cut back significantly
        "min_hours": 0,
        "max_hours": 16,
        "refit_channel_keys": ["Air Conditioner", "AC"],
    },
    "fan": {
        "label": "Ceiling / Table Fan",
        "avg_watts": 75,
        "flexibility": "medium",
        "min_hours": 2,
        "max_hours": 24,
        "refit_channel_keys": ["Fan"],
    },
    "television": {
        "label": "Television",
        "avg_watts": 120,
        "flexibility": "medium",
        "min_hours": 0,
        "max_hours": 12,
        "refit_channel_keys": ["Television", "TV", "TV Site"],
    },
    "lighting": {
        "label": "Lights",
        "avg_watts": 60,
        "flexibility": "low",
        "min_hours": 3,
        "max_hours": 14,
        "refit_channel_keys": ["Lighting", "Lights"],
    },
    "refrigerator": {
        "label": "Refrigerator",
        "avg_watts": 150,
        "flexibility": "none",       # always-on essential load
        "min_hours": 24,
        "max_hours": 24,
        "refit_channel_keys": ["Fridge", "Fridge-Freezer", "Freezer"],
    },
    "washing_machine": {
        "label": "Washing Machine",
        "avg_watts": 500,
        "flexibility": "high",
        "min_hours": 0,
        "max_hours": 3,
        "refit_channel_keys": ["Washing Machine"],
    },
    "computer": {
        "label": "Computer / Laptop",
        "avg_watts": 150,
        "flexibility": "medium",
        "min_hours": 0,
        "max_hours": 12,
        "refit_channel_keys": ["Computer", "Computer Site"],
    },
    "microwave": {
        "label": "Microwave",
        "avg_watts": 1200,
        "flexibility": "medium",
        "min_hours": 0,
        "max_hours": 2,
        "refit_channel_keys": ["Microwave"],
    },
}

FLEXIBILITY_WEIGHT = {"none": 0.0, "low": 0.25, "medium": 0.6, "high": 1.0}


class Settings(BaseSettings):
    # Simple flat tariff (INR per kWh) — swap for slab-based via `tariff_slabs`.
    tariff_flat_rate: float = 8.0

    # Optional slab-based tariff (kWh threshold, rate) applied cumulatively.
    tariff_slabs: list[tuple[float, float]] = [
        (100, 4.5),
        (200, 6.5),
        (500, 8.5),
        (float("inf"), 10.5),
    ]
    use_slab_tariff: bool = True

    model_store_dir: str = "models_store"
    processed_data_dir: str = "../data/processed"

    model_config = SettingsConfigDict(protected_namespaces=(), env_prefix="ENERGY_")


settings = Settings()


def estimate_cost(total_kwh: float) -> float:
    """Apply the configured tariff to a total energy consumption figure."""
    if not settings.use_slab_tariff:
        return round(total_kwh * settings.tariff_flat_rate, 2)

    remaining = total_kwh
    prev_threshold = 0.0
    cost = 0.0
    for threshold, rate in settings.tariff_slabs:
        slab_width = threshold - prev_threshold
        used = min(remaining, slab_width)
        if used <= 0:
            break
        cost += used * rate
        remaining -= used
        prev_threshold = threshold
    return round(cost, 2)
