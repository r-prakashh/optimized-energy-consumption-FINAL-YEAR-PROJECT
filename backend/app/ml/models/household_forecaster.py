"""Whole-household daily energy forecasting model (LightGBM).

Learns the business-as-usual consumption pattern (time-of-week effects,
seasonality via lag/rolling features) from REFIT aggregate data. Used to
produce a baseline forecast — "if nothing changes, this is roughly what
you'll consume" — before appliance-level adjustments are applied.
"""
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error

MODEL_DIR = Path(__file__).resolve().parents[3] / "models_store"
FEATURE_COLUMNS = [
    "day_of_week",
    "is_weekend",
    "month",
    "day_of_year",
    "lag_1d",
    "lag_7d",
    "rolling_mean_7d",
    "rolling_std_7d",
    "rolling_mean_30d",
]
TARGET_COLUMN = "total_kwh"


def _chronological_split_per_house(df: pd.DataFrame, test_size: float = 0.2):
    """
    Splits each house's own timeline into train/test (last `test_size`
    fraction of its dates held out), then concatenates across houses. A
    plain global chronological split (sorted by house then date) would put
    the entire test set inside whichever house sorts last — this instead
    guarantees every house contributes to both train and test.
    """
    train_parts, test_parts = [], []
    for _, group in df.groupby("house_id"):
        group = group.sort_values("date")
        cutoff = int(len(group) * (1 - test_size))
        train_parts.append(group.iloc[:cutoff])
        test_parts.append(group.iloc[cutoff:])
    return pd.concat(train_parts), pd.concat(test_parts)


def train(
    processed_path: Path,
    model_out: Path = MODEL_DIR / "household_forecaster.txt",
    feature_columns: list[str] = FEATURE_COLUMNS,
):
    """
    `feature_columns` defaults to the deployed feature set (no weather).
    Pass an extended list (see experiments/weather_ablation.py) to train a
    comparison model for reporting — the shipped model deliberately excludes
    weather since inference serves Tamil Nadu users while REFIT's weather
    signal is UK-specific (see app/ml/weather.py's module docstring).
    """
    df = pd.read_parquet(processed_path)
    df = df.dropna(subset=feature_columns + [TARGET_COLUMN])

    train_df, test_df = _chronological_split_per_house(df)
    X_train, y_train = train_df[feature_columns], train_df[TARGET_COLUMN]
    X_test, y_test = test_df[feature_columns], test_df[TARGET_COLUMN]

    model = lgb.LGBMRegressor(
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        max_depth=-1,
        min_child_samples=10,
        random_state=42,
    )
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = float(np.sqrt(np.mean((y_test - preds) ** 2)))
    mape = mean_absolute_percentage_error(y_test, preds)
    wmape = float(np.sum(np.abs(y_test - preds)) / np.sum(np.abs(y_test)))

    print(f"MAE:   {mae:.3f} kWh")
    print(f"RMSE:  {rmse:.3f} kWh")
    print(f"MAPE:  {mape:.3%}")
    print(f"WMAPE: {wmape:.3%}")

    model_out.parent.mkdir(parents=True, exist_ok=True)
    model.booster_.save_model(str(model_out))

    metrics = {"mae": mae, "rmse": rmse, "mape": mape, "wmape": wmape}
    joblib.dump(metrics, model_out.with_suffix(".metrics.pkl"))
    return model, metrics


class HouseholdForecaster:
    """Inference wrapper around the saved LightGBM booster."""

    def __init__(self, model_path: Path = MODEL_DIR / "household_forecaster.txt"):
        self.booster = lgb.Booster(model_file=str(model_path))

    def forecast_next_n_days(self, history_df: pd.DataFrame, n_days: int) -> list[float]:
        """
        history_df: dataframe of past daily records with columns
        ['date', 'total_kwh'] sorted ascending, at least 30 rows recommended.
        Returns a list of n_days predicted daily kWh values, recursively
        rolling lag/rolling features forward one day at a time.
        """
        history = history_df.copy().sort_values("date").reset_index(drop=True)
        predictions = []

        for step in range(n_days):
            last_date = history["date"].iloc[-1] + pd.Timedelta(days=1)
            row = {
                "day_of_week": last_date.dayofweek,
                "is_weekend": int(last_date.dayofweek in (5, 6)),
                "month": last_date.month,
                "day_of_year": last_date.dayofyear,
                "lag_1d": history["total_kwh"].iloc[-1],
                "lag_7d": history["total_kwh"].iloc[-7]
                if len(history) >= 7
                else history["total_kwh"].mean(),
                "rolling_mean_7d": history["total_kwh"].tail(7).mean(),
                "rolling_std_7d": history["total_kwh"].tail(7).std() or 0.0,
                "rolling_mean_30d": history["total_kwh"].tail(30).mean(),
            }
            X = pd.DataFrame([row])[FEATURE_COLUMNS]
            pred = float(self.booster.predict(X)[0])
            predictions.append(max(pred, 0.0))

            history = pd.concat(
                [history, pd.DataFrame([{"date": last_date, "total_kwh": pred}])],
                ignore_index=True,
            )

        return predictions
