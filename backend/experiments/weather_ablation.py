"""Ablation: does adding UK weather (temperature, heating-degree-days) as a
training feature improve the household forecaster's own held-out accuracy?

This answers "why is WMAPE ~23%, can it be improved" with a real, measured
comparison rather than a guess. Run after `build_dataset.py` (which already
joins weather columns onto household_daily.parquet):

    python -m experiments.weather_ablation

The weather-augmented model is NOT written to backend/models_store/ — it's
a reporting artifact only. The deployed model stays weather-free because
inference serves Tamil Nadu users, and REFIT's temperature-consumption
relationship (UK heating load) doesn't transfer to a cooling-driven climate
(see app/ml/weather.py). Results get pasted into README.md / Methodology.
"""
from pathlib import Path

from app.ml.models.household_forecaster import FEATURE_COLUMNS, train

PROCESSED_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "household_daily.parquet"
SCRATCH_MODEL_OUT = Path(__file__).resolve().parent / "_weather_ablation_model.txt"

WEATHER_FEATURE_COLUMNS = FEATURE_COLUMNS + ["temp_mean_c", "heating_degree_days"]


def main():
    print("=" * 60)
    print("BASELINE (no weather) — deployed feature set")
    print("=" * 60)
    _, baseline_metrics = train(PROCESSED_PATH, model_out=SCRATCH_MODEL_OUT)

    print()
    print("=" * 60)
    print("WEATHER-AUGMENTED (UK temperature + heating-degree-days)")
    print("=" * 60)
    _, weather_metrics = train(
        PROCESSED_PATH, model_out=SCRATCH_MODEL_OUT, feature_columns=WEATHER_FEATURE_COLUMNS
    )

    print()
    print("=" * 60)
    print("COMPARISON")
    print("=" * 60)
    for metric in ["mae", "rmse", "wmape"]:
        b, w = baseline_metrics[metric], weather_metrics[metric]
        delta_pct = (w - b) / b * 100
        print(f"{metric.upper():6s}  baseline={b:.4f}  weather={w:.4f}  ({delta_pct:+.1f}%)")

    SCRATCH_MODEL_OUT.unlink(missing_ok=True)
    SCRATCH_MODEL_OUT.with_suffix(".metrics.pkl").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
