"""Turn REFIT per-house CSVs into two model-ready datasets:

1. Household-level daily table  -> data/processed/household_daily.parquet
   Used to train the whole-house forecasting model (business-as-usual
   consumption forecast). Computed from the `Aggregate` column ONLY.

2. Appliance-level daily table  -> data/processed/appliance_daily.parquet
   Used to train per-appliance-category duty-cycle models (hours used ->
   energy consumed), grounding appliance analysis in real REFIT behaviour
   instead of pure wattage arithmetic. Computed from the individual
   `Appliance<N>` sub-metered columns.

REFIT CLEAN CSVs have columns: Time, Unix, Aggregate, Appliance1..Appliance9.
`Aggregate` is the whole-house total power draw — it already INCLUDES the
power drawn by the sub-metered appliances, so household-level totals must
come from `Aggregate` alone and must never be added to the appliance columns
(that double-counts and inflates consumption).

A per-house channel legend (which Appliance<N> is which physical device)
is not shipped with the raw data — fill it in in `HOUSE_APPLIANCE_MAP` below
from REFIT's official documentation before training the appliance model.
Houses without an entry are simply skipped for appliance-level training
(the household forecaster still uses all requested houses regardless).

Readings are irregularly timestamped (~6-8s nominal spacing but with real
gaps), so energy is computed by time-weighted integration (power * elapsed
seconds) rather than assuming a fixed sample interval. Gaps longer than
MAX_GAP_SECONDS are treated as missing data and contribute zero energy,
to avoid wildly overestimating consumption across outages / logger gaps.
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.config import APPLIANCE_CATALOG

# Points at the REFIT CLEAN files bundled in the project's dataset drop.
RAW_DIR = (
    Path(__file__).resolve().parents[4]
    / "data" / "raw" / "AI_Energy_Project" / "REFIT_CLEAN"
)
PROCESSED_DIR = Path(__file__).resolve().parents[4] / "data" / "processed"

APPLIANCE_COLUMNS = [f"Appliance{i}" for i in range(1, 10)]
MAX_GAP_SECONDS = 60  # beyond this, treat the gap as a logger outage, not usage

# Maps REFIT "Appliance<N>" columns to our generic catalog keys, per house.
# Fill in from REFIT's official per-house channel legend before training the
# appliance-level model. Left empty by default — see data/README.md.
HOUSE_APPLIANCE_MAP: dict[int, dict[str, str]] = {
    # Example once you have the channel legend for a house:
    # 1: {"Appliance2": "washing_machine", "Appliance6": "television"},
}


def _load_house_csv(house_id: int) -> pd.DataFrame:
    path = RAW_DIR / f"House_{house_id}_clean.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — see data/README.md for dataset setup."
        )
    df = pd.read_csv(
        path,
        usecols=["Time", "Aggregate", *APPLIANCE_COLUMNS],
        parse_dates=["Time"],
    )
    df = df.dropna(subset=["Time"]).sort_values("Time").reset_index(drop=True)

    # Time-weighted integration: seconds elapsed since the previous reading,
    # capped so logger gaps don't get counted as continuous high usage.
    dt = df["Time"].diff().dt.total_seconds()
    dt = dt.fillna(dt.median())
    df["_dt_seconds"] = dt.clip(lower=0, upper=MAX_GAP_SECONDS)
    df["date"] = df["Time"].dt.date
    return df


def _process_house(house_id: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (household_daily_rows, appliance_daily_rows) for one house."""
    df = _load_house_csv(house_id)
    dt_hours = df["_dt_seconds"] / 3600

    # --- household-level: Aggregate only, never combined with appliances ---
    df["_agg_wh"] = df["Aggregate"].fillna(0).clip(lower=0) * dt_hours
    household_daily = (
        df.groupby("date")["_agg_wh"].sum().div(1000).reset_index(name="total_kwh")
    )
    household_daily.insert(0, "house_id", house_id)

    # --- appliance-level: only for houses with a known channel mapping ---
    appliance_rows = []
    channel_map = HOUSE_APPLIANCE_MAP.get(house_id, {})
    for column, category in channel_map.items():
        if column not in df.columns:
            continue
        rating = APPLIANCE_CATALOG[category]["avg_watts"]
        on_threshold = rating * 0.10  # filters out standby/phantom load noise

        values = df[column].fillna(0).clip(lower=0)
        wh = values * dt_hours
        on_hours = np.where(values > on_threshold, dt_hours, 0.0)

        tmp = pd.DataFrame({"date": df["date"], "wh": wh, "on_hours": on_hours})
        daily = tmp.groupby("date").sum().reset_index()
        daily["house_id"] = house_id
        daily["appliance"] = category
        daily["energy_kwh"] = daily["wh"] / 1000
        daily["hours_on"] = daily["on_hours"]
        appliance_rows.append(daily[["house_id", "appliance", "date", "hours_on", "energy_kwh"]])

    appliance_daily = (
        pd.concat(appliance_rows, ignore_index=True) if appliance_rows else pd.DataFrame()
    )
    return household_daily, appliance_daily


def build_household_daily(house_ids: list[int]) -> pd.DataFrame:
    parts = [_process_house(h)[0] for h in house_ids]
    out = pd.concat(parts, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["house_id", "date"]).reset_index(drop=True)
    out = _add_time_features(out)
    out = _add_lag_features(out, target_col="total_kwh", group_col="house_id")
    return out.dropna().reset_index(drop=True)


def build_appliance_daily(house_ids: list[int]) -> pd.DataFrame:
    parts = [_process_house(h)[1] for h in house_ids]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame(
            columns=["house_id", "appliance", "date", "hours_on", "energy_kwh", "day_of_week", "is_weekend"]
        )
    out = pd.concat(parts, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out["day_of_week"] = out["date"].dt.dayofweek
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(int)
    return out.sort_values(["appliance", "house_id", "date"]).reset_index(drop=True)


def _add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    return df


def _add_lag_features(df: pd.DataFrame, target_col: str, group_col: str) -> pd.DataFrame:
    df = df.copy()
    grouped = df.groupby(group_col)[target_col]
    df["lag_1d"] = grouped.shift(1)
    df["lag_7d"] = grouped.shift(7)
    df["rolling_mean_7d"] = grouped.transform(lambda s: s.shift(1).rolling(7).mean())
    df["rolling_std_7d"] = grouped.transform(lambda s: s.shift(1).rolling(7).std())
    df["rolling_mean_30d"] = grouped.transform(lambda s: s.shift(1).rolling(30).mean())
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--houses", type=str, required=True, help="Comma-separated house IDs, e.g. 1,2,3"
    )
    args = parser.parse_args()
    house_ids = [int(h) for h in args.houses.split(",")]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Building household-level daily dataset for houses {house_ids}...")
    household_df = build_household_daily(house_ids)
    household_df.to_parquet(PROCESSED_DIR / "household_daily.parquet", index=False)
    print(f"  -> {len(household_df)} rows written.")

    print("Building appliance-level daily dataset...")
    appliance_df = build_appliance_daily(house_ids)
    appliance_df.to_parquet(PROCESSED_DIR / "appliance_daily.parquet", index=False)
    print(f"  -> {len(appliance_df)} rows written.")
    if appliance_df.empty:
        print(
            "  NOTE: no appliance-level rows — fill in HOUSE_APPLIANCE_MAP in "
            "this file with the REFIT channel legend for your houses first."
        )


if __name__ == "__main__":
    main()
