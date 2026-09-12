"""Per-appliance-category duty-cycle model.

For each appliance category (fan, AC, TV, ...), learns energy_kwh(hours_used,
day_of_week) from REFIT appliance channels pooled across houses. This captures
real duty-cycle effects (e.g. a fridge's compressor cycling, an AC's variable
load under thermostatic control) that a flat wattage x hours calculation
cannot, while still degrading gracefully to a wattage-based estimate when a
category has no REFIT-derived model (e.g. user selects an appliance category
absent from the training houses).
"""
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from typing import Any

from app.core.appliance_specs import compute_effective_watts
from app.core.config import APPLIANCE_CATALOG
from app.ml.weather import get_cached_tn_temperature

MODEL_DIR = Path(__file__).resolve().parents[3] / "models_store"
FEATURE_COLUMNS = ["hours_on", "day_of_week", "is_weekend"]
TARGET_COLUMN = "energy_kwh"

# AC energy scales with how hard the compressor works to hold a comfort
# setpoint — hotter days mean longer/heavier duty cycles. This is a
# transparent physics-motivated heuristic using live Tamil Nadu weather, kept
# deliberately separate from the REFIT-trained models (see app/ml/weather.py
# module docstring for why UK-trained weather sensitivity can't be reused for
# a cooling-driven climate).
AC_COMFORT_BASELINE_C = 24.0
AC_SENSITIVITY_PER_DEGREE = 0.04  # +4% energy per °C above baseline
AC_ADJUSTMENT_BOUNDS = (0.6, 1.6)


def _ac_temperature_multiplier(city: str = "chennai") -> float:
    temp = get_cached_tn_temperature(city)
    if temp is None:
        return 1.0
    raw = 1 + AC_SENSITIVITY_PER_DEGREE * (temp - AC_COMFORT_BASELINE_C)
    return max(AC_ADJUSTMENT_BOUNDS[0], min(AC_ADJUSTMENT_BOUNDS[1], raw))


def train(processed_path: Path, model_out_dir: Path = MODEL_DIR / "appliance_models"):
    df = pd.read_parquet(processed_path)
    model_out_dir.mkdir(parents=True, exist_ok=True)

    trained = {}
    for category, group in df.groupby("appliance"):
        if len(group) < 20:
            print(f"Skipping '{category}': only {len(group)} rows (need >= 20).")
            continue

        X = group[FEATURE_COLUMNS]
        y = group[TARGET_COLUMN]
        model = LinearRegression(positive=True)  # energy can't be negative
        model.fit(X, y)

        r2 = model.score(X, y)
        print(f"{category}: R^2={r2:.3f}, n={len(group)}")

        joblib.dump(model, model_out_dir / f"{category}.pkl")
        trained[category] = r2

    return trained


class ApplianceModel:
    """
    Estimates daily energy (kWh) for a given appliance category and number of
    hours used per day. Falls back to nameplate-wattage arithmetic when no
    REFIT-trained model exists for that category.
    """

    def __init__(self, model_dir: Path = MODEL_DIR / "appliance_models"):
        self.models: dict[str, LinearRegression] = {}
        if model_dir.exists():
            for path in model_dir.glob("*.pkl"):
                self.models[path.stem] = joblib.load(path)

    def estimate_kwh(
        self,
        category: str,
        hours_per_day: float,
        day_of_week: int = 0,
        specs: dict[str, Any] | None = None,
    ) -> float:
        is_weekend = int(day_of_week in (5, 6))
        catalog_entry = APPLIANCE_CATALOG.get(category)
        if catalog_entry is None:
            raise ValueError(f"Unknown appliance category: {category}")

        if category in self.models:
            # A REFIT-trained duty-cycle model exists for this category —
            # specs aren't used here (the model already reflects real
            # hours-to-energy behaviour); specs only refine the wattage
            # fallback path below.
            X = pd.DataFrame(
                [{"hours_on": hours_per_day, "day_of_week": day_of_week, "is_weekend": is_weekend}]
            )
            base = max(float(self.models[category].predict(X)[0]), 0.0)
        else:
            effective_watts = compute_effective_watts(
                category, catalog_entry["avg_watts"], specs or {}
            )
            base = (effective_watts * hours_per_day) / 1000

        if category == "air_conditioner":
            base *= _ac_temperature_multiplier()

        return base
