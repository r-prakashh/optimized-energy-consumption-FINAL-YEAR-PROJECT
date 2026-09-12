# WattWise — AI-Based Personalized Energy Consumption Forecasting & Cost Optimization

A household energy management web app that predicts electricity consumption,
estimates electricity cost, and produces a **budget-constrained appliance
usage plan**. Built on the REFIT Electrical Load Measurements dataset.

Pipeline: `Budget + Duration + Appliances → REFIT-trained forecasting → appliance-level
analysis → cost estimation → budget optimization → recommended appliance hours → what-if`

## Stack

- **Backend:** FastAPI + LightGBM (household forecasting) + scikit-learn (per-appliance
  duty-cycle models) + a transparent rule-based budget optimizer.
- **Frontend:** React + TypeScript + Vite + Recharts.
- **Data:** REFIT Electrical Load Measurements (public dataset — see [data/README.md](data/README.md)).
- **Hosting (free tier only):** backend on Render, frontend on Vercel/Netlify.

## Why this design (for the project report)

- **Forecasting ≠ the whole story.** The system explicitly chains "how much
  energy" → "how much will it cost" → "how should usage be planned to hit a
  budget" — see [backend/app/api/routes.py](backend/app/api/routes.py) for
  the `/plan` pipeline.
- **Two-part consumption model**, not just wattage arithmetic:
  1. [household_forecaster.py](backend/app/ml/models/household_forecaster.py) —
     a LightGBM regressor trained on REFIT daily aggregates with time,
     lag (1d/7d), and rolling-window (7d/30d) features. This produces the
     business-as-usual baseline forecast for the requested duration.
  2. [appliance_model.py](backend/app/ml/models/appliance_model.py) — per
     appliance-category regressors trained on REFIT's individual appliance
     channels, mapping `hours_used_per_day → energy_kwh` while capturing
     real duty-cycle behavior (falls back to nameplate-wattage arithmetic
     for categories absent from the training houses).
- **Explainable optimization, not RL.** [optimizer.py](backend/app/optimization/optimizer.py)
  greedily trims hours on the most flexible, highest-draw appliance first,
  respecting per-appliance `min_hours` (e.g. a fridge is never told to
  switch off). Every recommendation traces back to flexibility class,
  relative consumption share, and the remaining budget gap.
- **What-if is just a re-run**, not a separate model — see the `/what-if`
  endpoint, which reuses the identical pipeline with modified inputs.

## Project layout

```
backend/
  app/
    api/routes.py              REST endpoints: /appliances, /plan, /what-if
    core/config.py             Appliance catalog, tariff logic
    ml/preprocessing/          REFIT -> model-ready parquet datasets
    ml/models/                 Household forecaster + appliance duty-cycle models
    optimization/optimizer.py  Budget-constrained rule-based optimizer
    schemas/                   Pydantic request/response models
  models_store/                Trained model artifacts (committed — small, KBs-MBs)
frontend/
  src/
    api/client.ts              Typed API client
    components/                ApplianceSelector, ForecastChart, PlanResults
    App.tsx                    Main flow
data/
  raw/                         REFIT CSVs (gitignored — see data/README.md)
  processed/                   Feature-engineered parquet files (gitignored)
notebooks/                     Exploratory analysis / model evaluation notebooks
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
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

App at `http://localhost:5173`. Set `VITE_API_BASE_URL` in a `.env` file if
the backend isn't at `http://localhost:8000/api`.

### Training the model (optional — a pretrained model already ships in `backend/models_store/`)

```bash
cd backend
python -m app.ml.preprocessing.build_dataset --houses 1,2,3,4,5
python -c "from pathlib import Path; from app.ml.models import household_forecaster as h; h.train(Path('../data/processed/household_daily.parquet'))"
python -c "from pathlib import Path; from app.ml.models import appliance_model as a; a.train(Path('../data/processed/appliance_daily.parquet'))"
```

The shipped model was trained on REFIT houses 1-5 (2,704 house-days). Held-out
evaluation (chronological split *within each house*, not just the tail of
the last house — see `_chronological_split_per_house` in
[household_forecaster.py](backend/app/ml/models/household_forecaster.py)):

| Metric | Value |
|---|---|
| MAE   | 2.56 kWh/day |
| RMSE  | 3.77 kWh/day |
| WMAPE | 23.3% |
| MAPE  | 63.2% (unreliable here — several test days have near-zero true consumption, which blows up any percentage metric with a near-zero denominator; **WMAPE is the metric to trust** for this dataset) |

The appliance-level model currently runs on nameplate-wattage arithmetic
rather than REFIT-calibrated duty cycles — see
[data/README.md](data/README.md#appliance-channel-legend--resolved-as-a-deliberate-scope-decision)
for why (REFIT's official per-house channel legend wasn't available, and an
attempted automatic signature-based classifier proved unreliable on this
data — a documented, deliberate scope decision, not an oversight).

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
  (`original_cost - projected_cost`), and distribution of hour reductions
  across appliance flexibility classes.

## Scope note

This is a software forecasting/optimization platform, not a smart-meter
hardware project or an exact billing system — outputs are approximate
estimates grounded in REFIT-derived patterns and nameplate appliance
ratings, intended for proactive household planning rather than
meter-accurate billing.
