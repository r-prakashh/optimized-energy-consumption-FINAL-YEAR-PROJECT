# Dataset Setup — REFIT Electrical Load Measurements

The raw REFIT CSVs are **not committed to this repo** (multi-GB, exceeds GitHub's
file/repo limits and would make cloning painful for anyone reviewing the project).
Only trained model artifacts under `backend/models_store/` are versioned — those
are what the app actually needs to run for a demo.

## Current setup

The dataset (`AI_Energy_Project.7z`) has already been downloaded and extracted
into:

```
data/raw/AI_Energy_Project/
  REFIT_RAW/       (not present — original raw REFIT files, not needed further)
  REFIT_CLEAN/     House_1_clean.csv ... House_21_clean.csv (no House_14 — REFIT skips it)
                    columns: Time, Unix, Aggregate, Appliance1..Appliance9
  MODEL_DATA/      House_N_daily.csv / House_N_ML.csv — a friend's own preprocessing pass
  plots/           exploratory PNGs
  preprocess_refit.py
```

**Important — do not use `MODEL_DATA/*.csv` for the household forecasting
target.** `preprocess_refit.py`'s `aggregate_power` column sums `Aggregate`
(the whole-house total) **plus** the individual `Appliance1..9` columns —
but `Aggregate` already includes that appliance power, so `aggregate_power`
double-counts and overstates consumption by roughly 10-30%. This project's
own pipeline ([build_dataset.py](../backend/app/ml/preprocessing/build_dataset.py))
reads `REFIT_CLEAN/*.csv` directly and computes household energy from
`Aggregate` alone, with time-weighted integration over the real (irregular)
sample timestamps rather than assuming a fixed interval.

## Appliance channel legend — resolved as a deliberate scope decision

`Appliance1`..`Appliance9` are anonymous per-house channel numbers; which
physical appliance each one is (fridge, washing machine, TV, ...) is defined
by REFIT's official channel legend, which isn't bundled in this drop.

Two options were evaluated:

1. **Hardcode a remembered mapping** — rejected: risks silently training the
   appliance model on wrong labels, which is worse than not having it.
2. **Auto-infer the category from each channel's own signature** (duty cycle,
   power level, time-of-day) — implemented in
   [classify_channels.py](../backend/app/ml/preprocessing/classify_channels.py)
   as a runnable experiment. Result: unreliable on this data (implausible
   label distribution, and multi-kW spikes even on otherwise low-power
   channels, consistent with sensor noise/cross-talk). Its output is
   documented but intentionally **not** wired into `build_dataset.py`.

**Final design:** `HOUSE_APPLIANCE_MAP` in `build_dataset.py` stays empty by
default, and the appliance-level model deliberately falls back to nameplate-
wattage arithmetic (`app/ml/models/appliance_model.py`) — fully functional,
matching the "approximate power ratings" path described in the project
abstract. If you later obtain REFIT's verified official channel legend, fill
in `HOUSE_APPLIANCE_MAP` with real per-house mappings and re-run the build +
retrain to switch specific appliances over to REFIT-calibrated duty-cycle
models — the code path already supports it per-category, no other changes
needed.

## Rebuilding the processed datasets

```bash
cd backend
python -m app.ml.preprocessing.build_dataset --houses 1,2,3,4,5
```

Reads `data/raw/AI_Energy_Project/REFIT_CLEAN/`, writes compact parquet files
to `data/processed/` (household_daily.parquet, appliance_daily.parquet).

## You do NOT need this to just run the app

The app ships with a pretrained model in `backend/models_store/`. Cloning the
repo and running `uvicorn` / the frontend works immediately — this dataset
step is only needed if you want to retrain or extend to more houses/appliances.
