from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from fastapi import APIRouter

from app.core.appliance_specs import get_specs_schema
from app.core.config import APPLIANCE_CATALOG
from app.ml.models.appliance_model import ApplianceModel
from app.ml.models.household_forecaster import HouseholdForecaster, MODEL_DIR
from app.optimization.action_plan import generate_action_plan
from app.optimization.optimizer import ApplianceUsage, optimize
from app.schemas.plan import PlanRequest, PlanResponse, WhatIfRequest

router = APIRouter()

_appliance_model = ApplianceModel()

_household_model_path = MODEL_DIR / "household_forecaster.txt"
_household_forecaster = (
    HouseholdForecaster(_household_model_path) if _household_model_path.exists() else None
)


@router.get("/appliances")
def list_appliances():
    """Appliance catalog for the frontend to render selection checkboxes,
    each annotated with its optional spec fields (e.g. AC tonnage/star
    rating) for a per-model, not just per-category, estimate."""
    specs_schema = get_specs_schema()
    return [
        {
            "category": key,
            **{k: v for k, v in val.items() if k != "refit_channel_keys"},
            "specs": specs_schema.get(key, []),
        }
        for key, val in APPLIANCE_CATALOG.items()
    ]


def _baseline_forecast(usages: list[ApplianceUsage], duration_days: int) -> list[float]:
    """
    Household-level baseline forecast for the period. Uses the trained
    LightGBM model if available (seeded with a synthetic recent-history
    window built from the user's own appliance selection); otherwise falls
    back to a simple weekday/weekend-aware sum of appliance estimates.
    """
    if _household_forecaster is not None:
        today = date.today()
        history_dates = [today - timedelta(days=30 - i) for i in range(30)]
        history_kwh = [
            sum(
                _appliance_model.estimate_kwh(u.category, u.hours_per_day, d.weekday(), u.specs)
                for u in usages
            )
            for d in history_dates
        ]
        history_df = pd.DataFrame({"date": pd.to_datetime(history_dates), "total_kwh": history_kwh})
        return _household_forecaster.forecast_next_n_days(history_df, duration_days)

    today = date.today()
    return [
        sum(
            _appliance_model.estimate_kwh(
                u.category, u.hours_per_day, (today + timedelta(days=i)).weekday(), u.specs
            )
            for u in usages
        )
        for i in range(duration_days)
    ]


def _run_plan(payload: PlanRequest) -> PlanResponse:
    usages = [ApplianceUsage(a.category, a.hours_per_day, a.specs) for a in payload.appliances]
    specs_by_category = {a.category: a.specs for a in payload.appliances}

    forecast = _baseline_forecast(usages, payload.duration_days)

    result = optimize(
        usages=usages,
        duration_days=payload.duration_days,
        budget=payload.budget,
        appliance_model=_appliance_model,
    )
    action_plan = generate_action_plan(result, specs_by_category)

    return PlanResponse(
        projected_daily_kwh=result.projected_daily_kwh,
        projected_total_kwh=result.projected_total_kwh,
        projected_cost=result.projected_cost,
        original_cost=result.original_cost,
        budget=result.budget,
        budget_met=result.budget_met,
        duration_days=result.duration_days,
        appliances=[
            {
                "category": a.category,
                "label": a.label,
                "original_hours": a.original_hours,
                "recommended_hours": a.recommended_hours,
                "daily_kwh": a.daily_kwh,
                "reduced": a.reduced,
            }
            for a in result.appliances
        ],
        forecast_daily_kwh=[round(v, 3) for v in forecast],
        tod_shift_opportunities=[
            {
                "category": o.category,
                "label": o.label,
                "daily_kwh": o.daily_kwh,
                "estimated_saving_per_day": o.estimated_saving,
            }
            for o in result.tod_shift_opportunities
        ],
        tod_total_saving_for_period=round(result.tod_total_saving * payload.duration_days, 2),
        action_plan=action_plan,
    )


@router.post("/plan", response_model=PlanResponse)
def create_plan(payload: PlanRequest):
    """
    Main pipeline endpoint: forecast -> appliance analysis -> cost estimate
    -> budget optimization -> recommended appliance hours.
    """
    return _run_plan(payload)


@router.post("/what-if", response_model=PlanResponse)
def what_if(payload: WhatIfRequest):
    """
    Re-runs cost estimation + optimization (and forecast, since duration or
    appliance selection may have changed) with modified inputs. Kept as a
    separate endpoint for clarity in the frontend/API, even though the
    underlying computation is identical to /plan.
    """
    return _run_plan(payload)
