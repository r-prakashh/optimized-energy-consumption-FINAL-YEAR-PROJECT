from pydantic import BaseModel, Field


class ApplianceInput(BaseModel):
    category: str = Field(..., description="Appliance catalog key, e.g. 'air_conditioner'")
    hours_per_day: float = Field(..., ge=0, le=24)


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


class WhatIfRequest(PlanRequest):
    """Same shape as PlanRequest — what-if is just a re-run with modified inputs."""
    pass
