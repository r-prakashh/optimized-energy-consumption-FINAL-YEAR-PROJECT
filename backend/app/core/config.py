"""Central configuration: TNEB tariff slabs, the appliance catalog, and an
illustrative time-of-day (ToD) tariff used by the load-shifting optimizer.

Appliance wattages are typical nameplate/approximate ratings (documented in
the project report) used as the physics-based baseline; REFIT-derived
duty-cycle models (see app/ml/models/appliance_model.py) refine these into
realistic energy-per-hour-used figures per appliance category where REFIT
data supports it.

Scope note: this project targets Tamil Nadu households, while the
forecasting model is trained on REFIT (UK) data — see
app/ml/weather.py and data/README.md for how that gap is handled.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


# Generic appliance categories the system supports, chosen to reflect a
# typical Tamil Nadu household (AC/fan-driven cooling load rather than UK-
# style heating; motor pump and water heater/geyser added as common local
# loads not present in REFIT's UK appliance mix).
APPLIANCE_CATALOG = {
    "air_conditioner": {
        "label": "Air Conditioner",
        "avg_watts": 1500,
        "flexibility": "high",       # can be cut back significantly
        "min_hours": 0,
        "max_hours": 16,
        "shiftable": False,          # thermal comfort load — not shiftable to off-peak hours
        "refit_channel_keys": ["Air Conditioner", "AC"],
    },
    "fan": {
        "label": "Ceiling / Table Fan",
        "avg_watts": 75,
        "flexibility": "medium",
        "min_hours": 2,
        "max_hours": 24,
        "shiftable": False,
        "refit_channel_keys": ["Fan"],
    },
    "television": {
        "label": "Television",
        "avg_watts": 120,
        "flexibility": "medium",
        "min_hours": 0,
        "max_hours": 12,
        "shiftable": False,
        "refit_channel_keys": ["Television", "TV", "TV Site"],
    },
    "lighting": {
        "label": "Lights",
        "avg_watts": 60,
        "flexibility": "low",
        "min_hours": 3,
        "max_hours": 14,
        "shiftable": False,
        "refit_channel_keys": ["Lighting", "Lights"],
    },
    "refrigerator": {
        "label": "Refrigerator",
        "avg_watts": 150,
        "flexibility": "none",       # always-on essential load
        "min_hours": 24,
        "max_hours": 24,
        "shiftable": False,
        "refit_channel_keys": ["Fridge", "Fridge-Freezer", "Freezer"],
    },
    "washing_machine": {
        "label": "Washing Machine",
        "avg_watts": 500,
        "flexibility": "high",
        "min_hours": 0,
        "max_hours": 3,
        "shiftable": True,           # runs unattended — a textbook off-peak shift candidate
        "refit_channel_keys": ["Washing Machine"],
    },
    "computer": {
        "label": "Computer / Laptop",
        "avg_watts": 150,
        "flexibility": "medium",
        "min_hours": 0,
        "max_hours": 12,
        "shiftable": False,
        "refit_channel_keys": ["Computer", "Computer Site"],
    },
    "microwave": {
        "label": "Microwave",
        "avg_watts": 1200,
        "flexibility": "medium",
        "min_hours": 0,
        "max_hours": 2,
        "shiftable": False,
        "refit_channel_keys": ["Microwave"],
    },
    "water_heater": {
        "label": "Water Heater / Geyser",
        "avg_watts": 2000,
        "flexibility": "high",
        "min_hours": 0,
        "max_hours": 3,
        "shiftable": True,           # can be pre-heated at night, no comfort loss
        "refit_channel_keys": [],
    },
    "motor_pump": {
        "label": "Water Motor Pump",
        "avg_watts": 750,
        "flexibility": "high",
        "min_hours": 0,
        "max_hours": 2,
        "shiftable": True,           # overhead-tank fill can run any time of day
        "refit_channel_keys": [],
    },
}

FLEXIBILITY_WEIGHT = {"none": 0.0, "low": 0.25, "medium": 0.6, "high": 1.0}


class Settings(BaseSettings):
    # Simple flat tariff (INR per kWh) — swap for slab-based via `tariff_slabs`.
    tariff_flat_rate: float = 8.0

    # TNEB domestic LT-IA tariff, monthly-equivalent slabs (TNERC Tariff
    # Order No. 6 of 2025, effective 1 Jul 2025). Real utility tariffs are
    # revised periodically (plus a quarterly fuel-cost adjustment) — verify
    # against the current TNERC order before relying on this for real bills.
    # (threshold_kwh_per_month, rate_per_kwh)
    tariff_slabs: list[tuple[float, float]] = [
        (100, 0.0),
        (200, 4.70),
        (300, 6.30),
        (400, 8.40),
        (float("inf"), 11.55),
    ]
    use_slab_tariff: bool = True

    # Illustrative ToD tariff for the load-shifting optimizer. Tamil Nadu's
    # residential tariff is NOT time-of-day priced today — this models where
    # several Indian discoms are piloting/heading, so the shifting feature
    # has a real (if simulated) price signal to optimize against, clearly
    # labeled as such in the UI rather than presented as TNEB's live tariff.
    tod_peak_hours: tuple[int, int] = (18, 22)   # 6pm-10pm
    tod_peak_multiplier: float = 1.3
    tod_offpeak_multiplier: float = 0.75

    model_store_dir: str = "models_store"
    processed_data_dir: str = "../data/processed"

    model_config = SettingsConfigDict(protected_namespaces=(), env_prefix="ENERGY_")


settings = Settings()


def estimate_cost(total_kwh: float, duration_days: int = 30) -> float:
    """
    Apply the TNEB slab tariff to a total energy consumption figure over
    `duration_days`. Slab thresholds are monthly, so they're prorated
    linearly to the requested duration (e.g. a 7-day plan sees 7/30ths of
    each monthly threshold) — an approximation, since TNEB actually bills
    bi-monthly with telescopic slabs, but a reasonable one for a planning
    tool operating on arbitrary day ranges.
    """
    if not settings.use_slab_tariff:
        return round(total_kwh * settings.tariff_flat_rate, 2)

    scale = duration_days / 30
    remaining = total_kwh
    prev_threshold = 0.0
    cost = 0.0
    for threshold, rate in settings.tariff_slabs:
        scaled_threshold = threshold * scale if threshold != float("inf") else threshold
        slab_width = scaled_threshold - prev_threshold
        used = min(remaining, slab_width)
        if used <= 0:
            break
        cost += used * rate
        remaining -= used
        prev_threshold = scaled_threshold
    return round(cost, 2)
