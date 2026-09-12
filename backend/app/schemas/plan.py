from typing import Any

from pydantic import BaseModel, Field


class ApplianceInput(BaseModel):
    category: str = Field(..., description="Appliance catalog key, e.g. 'air_conditioner'")
    hours_per_day: float = Field(..., ge=0, le=24)
    specs: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional model specs (e.g. {'capacity_ton': 1.5, 'star_rating': 5}) — see /appliances for the schema per category.",
    )


class PlanRequest(BaseModel):
    budget: float = Field(..., gt=0, description="Target electricity budget for the period")
    duration_days: int = Field(..., gt=0, le=90)
    appliances: list[ApplianceInput]


class ApplianceResultOut(BaseModel):
    category: str
    label: str
    original_hours: float
    recommended_hours: float
    daily_kwh: float
    reduced: bool


class TodShiftOpportunityOut(BaseModel):
    category: str
    label: str
    daily_kwh: float
    estimated_saving_per_day: float


class PlanResponse(BaseModel):
    projected_daily_kwh: float
    projected_total_kwh: float
    projected_cost: float
    original_cost: float
    budget: float
    budget_met: bool
    duration_days: int
    appliances: list[ApplianceResultOut]
    forecast_daily_kwh: list[float] = Field(
        default_factory=list,
        description="Household-level baseline forecast for the period (pre-optimization context)",
    )
    tod_shift_opportunities: list[TodShiftOpportunityOut] = Field(default_factory=list)
    tod_total_saving_for_period: float = Field(
        0.0,
        description=(
            "Illustrative saving over the full period if shiftable appliances moved to "
            "off-peak hours under a simulated time-of-day tariff (TNEB doesn't bill ToD "
            "today — see Settings.tod_peak_multiplier)."
        ),
    )
    action_plan: list[str] = Field(
        default_factory=list,
        description="Plain-language, per-appliance recommendations derived from the numeric plan.",
    )


class WhatIfRequest(PlanRequest):
    """Same shape as PlanRequest — what-if is just a re-run with modified inputs."""
    pass
