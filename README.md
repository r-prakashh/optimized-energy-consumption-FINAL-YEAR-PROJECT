# WattWise — AI-Based Personalized Energy Consumption Forecasting & Cost Optimization

A household energy management web app for **Tamil Nadu households**: it
predicts electricity consumption, estimates electricity cost against TNEB's
tariff, and produces a **budget-constrained appliance usage plan** — with a
live-weather-adjusted AC load estimate and a simulated time-of-day load-shift
analysis on top.

Rather than one flat wattage per appliance category, users can enter the
actual model specs they own — AC tonnage + BEE star rating + inverter,
refrigerator capacity + star rating, washing machine capacity + load type,
fan motor type, TV screen size — and the estimate is computed from that (see
[appliance_specs.py](backend/app/core/appliance_specs.py)). The plan comes
back with a plain-language **action plan** per appliance (keep/cut hours,
efficiency upgrade suggestions quantified from the same spec math, ToD shift
tips), not just a numbers table.

Pipeline: `Budget + Duration + Appliances (+ model specs) → forecasting →
appliance-level analysis (+ live TN weather) → TNEB cost estimation → budget
optimization → recommended appliance hours → action plan → ToD shift
opportunities → what-if`

## Stack

- **Backend:** FastAPI + LightGBM (household forecasting) + scikit-learn (per-appliance
  duty-cycle models) + a transparent rule-based budget optimizer.
- **Frontend:** React + TypeScript + Vite + React Router + Recharts — a multi-page
  site (landing, step-wizard planner, methodology) rather than a single form.
- **Data:** REFIT Electrical Load Measurements (public, UK — see [data/README.md](data/README.md))
  for training, plus live Open-Meteo weather (free, no key) for TN inference-time adjustment.
- **Hosting (free tier only):** backend on Render, frontend on Vercel/Netlify.

## Scope: built for Tamil Nadu, trained on UK data

The only public appliance-level household dataset available is REFIT — 20 UK
homes. That's a real, deliberately-documented gap: UK homes are
heating-dominated (gas boilers, barely any AC), Tamil Nadu homes are
cooling-dominated (AC/fan-driven, no heating). Rather than pretend this away:

- The household forecaster uses time/lag/rolling features that transfer
  across climates fine (weekday rhythm, autocorrelation) — nothing UK-specific.
- **Weather was tested as a forecaster feature and rejected on evidence, not
  assumption** — see the ablation below. It's also never fed a TN value into
  a UK-trained relationship, for the domain-mismatch reason above.
- **AC load gets a separate, transparent physics adjustment** — live Chennai/TN
  temperature (Open-Meteo) scales the AC estimate around a 24°C comfort
  baseline, entirely outside the REFIT-trained model.
- Appliance catalog, tariff, and the ToD-shift feature are all TN-specific
  (TNEB slabs, water heater/motor pump as loads REFIT never had).

Full writeup with citations: the in-app [Methodology page](frontend/src/pages/Methodology.tsx).

## Why this design (for the project report)

- **Forecasting ≠ the whole story.** The system explicitly chains "how much
  energy" → "how much will it cost" → "how should usage be planned to hit a
  budget" — see [backend/app/api/routes.py](backend/app/api/routes.py) for
  the `/plan` pipeline.
- **Two-part consumption model**, not just wattage arithmetic:
  1. [household_forecaster.py](backend/app/ml/models/household_forecaster.py) —
     a LightGBM regressor trained on REFIT daily aggregates with time,
     lag (1d/7d), and rolling-window (7d/30d) features.
  2. [appliance_model.py](backend/app/ml/models/appliance_model.py) — per
     appliance-category regressors trained on REFIT's individual appliance
     channels where available (falls back to nameplate-wattage arithmetic
     otherwise), plus a live-weather multiplier specifically for AC.
- **Explainable optimization, not RL.** [optimizer.py](backend/app/optimization/optimizer.py)
  greedily trims hours on the most flexible, highest-draw appliance first,
  respecting per-appliance `min_hours`. Every recommendation traces back to
  flexibility class, relative consumption share, and the remaining budget gap.
- **Time-of-day shift analysis, kept separate from real billing.** TNEB
  doesn't bill ToD today; the optimizer's `_estimate_tod_shift_savings`
  computes an illustrative saving for shiftable loads (washing machine, water
  heater, motor pump) under a simulated peak/off-peak price signal, clearly
  labeled "Simulated" in the UI, never blended into the real TNEB-slab cost.
- **What-if is just a re-run**, not a separate model — see the `/what-if`
  endpoint, which reuses the identical pipeline with modified inputs.

## Household forecaster accuracy — and an honest ablation

Shipped model: LightGBM trained on REFIT houses 1-5 (2,704 house-days).
Held out chronologically *within each house* (not just the tail of the last
house — see `_chronological_split_per_house`):

| Metric | Value |
|---|---|
| MAE   | 2.56 kWh/day |
| RMSE  | 3.77 kWh/day |
| WMAPE | 23.3% |
| MAPE  | 63.2% (unreliable — several test days have near-zero true consumption, which blows up any percentage metric with a near-zero denominator; **WMAPE is the metric to trust**) |

For context, single-household day-ahead forecasting typically runs 20-40%
WMAPE in published literature (individual homes are noisy in a way grid-level
forecasts, which average thousands of households, aren't).

**Does adding weather improve it?** Tested via [experiments/weather_ablation.py](backend/experiments/weather_ablation.py)
(Loughborough historical temperature + heating-degree-days, since REFIT
houses are real UK homes where that's a legitimate feature to test):

| Metric | Baseline | +Weather | Δ |
|---|---|---|---|
| MAE   | 2.556 | 2.622 | +2.6% |
| RMSE  | 3.773 | 3.801 | +0.8% |
| WMAPE | 23.34% | 23.94% | +2.6% |

Weather made it slightly **worse**, not better — the existing lag/rolling/
day-of-year features already seem to capture most of the seasonal variance
weather would explain. The deployed model excludes weather for two
independent reasons now: this measured result, and the domain-mismatch
argument above (TN inference has no UK weather-consumption relationship to
apply anyway).

## Appliance-channel mapping — a deliberate scope decision, not a gap

REFIT's official per-house appliance-channel legend (which numbered channel
is which physical device) isn't available in this project's dataset drop. An
automatic signature-based classifier ([classify_channels.py](backend/app/ml/preprocessing/classify_channels.py))
was built and tested — it produced an implausible label distribution and
multi-kW spikes even on otherwise low-power channels (sensor noise/cross-talk
in this data), so its output is documented but **not** wired into training.
The appliance-level model runs on nameplate-wattage arithmetic instead — see
[data/README.md](data/README.md) for the full writeup.

## Project layout

```
backend/
  app/
    api/routes.py              REST endpoints: /appliances, /plan, /what-if
    core/config.py             TN appliance catalog, TNEB tariff, ToD settings
    ml/weather.py              Open-Meteo: UK training weather + live TN weather (cached)
    ml/preprocessing/          REFIT -> model-ready parquet datasets (+ weather join)
    ml/models/                 Household forecaster + appliance duty-cycle models
    optimization/optimizer.py  Budget optimizer + ToD shift-savings analysis
    schemas/                   Pydantic request/response models
  experiments/weather_ablation.py  Reporting-only accuracy comparison (not deployed)
  models_store/                Trained model artifacts (committed — small, KBs-MBs)
frontend/
  src/
    api/client.ts              Typed API client
    pages/                     Home (landing), Plan (step-wizard planner), Methodology
    components/                Appliance selector/icons, forecast chart, donut chart,
                                budget gauge, before/after bars, ToD shift card
data/
  raw/                         REFIT CSVs (gitignored — see data/README.md)
  processed/                   Feature-engineered parquet files (gitignored)
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows; .venv\Scripts\activate for cmd.exe
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App at `http://localhost:5173` — landing page, `/plan` for the planner,
`/methodology` for the full writeup. Set `VITE_API_BASE_URL` in a `.env` file
if the backend isn't at `http://localhost:8000/api`.

### Retraining (optional — a pretrained model already ships in `backend/models_store/`)

```bash
cd backend
python -m app.ml.preprocessing.build_dataset --houses 1,2,3,4,5   # joins UK weather too
python -c "from pathlib import Path; from app.ml.models import household_forecaster as h; h.train(Path('../data/processed/household_daily.parquet'))"
python -c "from pathlib import Path; from app.ml.models import appliance_model as a; a.train(Path('../data/processed/appliance_daily.parquet'))"
python -m experiments.weather_ablation   # optional: reproduce the accuracy comparison above
```

## Deployment (free tier)

**Backend (Render):** push to GitHub → New Web Service on Render → connect
the repo → it auto-detects `render.yaml` (root dir `backend`, free plan).
First request after idle takes ~30-60s to wake (free tier sleeps after
inactivity) — expected, not a bug.

**Frontend (Vercel):** New Project → import the repo → set root directory to
`frontend` → add env var `VITE_API_BASE_URL=<your-render-url>/api` → deploy.
`vercel.json` handles the SPA rewrite. Netlify works identically if preferred.

## Evaluation

- **Forecasting:** MAE, RMSE, MAPE, WMAPE on a chronological hold-out split
  (printed by `household_forecaster.train`, saved to `*.metrics.pkl`).
- **Optimization:** budget adherence (`budget_met`), cost reduction achieved
  (`original_cost - projected_cost`), distribution of hour reductions across
  appliance flexibility classes, and simulated ToD shift savings for
  unattended loads.

## Scope note

This is a software forecasting/optimization platform, not a smart-meter
hardware project or an exact billing system — outputs are approximate
estimates intended for proactive household planning rather than
meter-accurate billing. See "Scope & limitations" on the in-app Methodology
page for the fully-detailed writeup.
