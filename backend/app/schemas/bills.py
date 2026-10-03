from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BillReadingIn(BaseModel):
    period_end: date = Field(..., description="Bill / reading date (end of the billing period)")
    period_days: int = Field(30, ge=7, le=92, description="Billing period length (TNEB: usually 60)")
    units_kwh: float = Field(..., ge=0, le=20000)
    amount_inr: float | None = Field(None, ge=0)


class BillAnalysisRequest(BaseModel):
    readings: list[BillReadingIn] = Field(..., min_length=1, max_length=60)
    horizon_months: int = Field(3, ge=1, le=12)


class ParsedReadingOut(BaseModel):
    period_end: str | None
    period_days: int
    units_kwh: float | None
    amount_inr: float | None = None
    previous_reading: float | None = None
    current_reading: float | None = None
    confidence: float
    source: str
    notes: list[str] = Field(default_factory=list)


class BillUploadResult(BaseModel):
    filename: str
    method: str
    ocr_confidence: float | None = None
    readings: list[ParsedReadingOut]
    raw_text_preview: str = ""
    error: str | None = None


class BillUploadResponse(BaseModel):
    files: list[BillUploadResult]
    ai_vision_used: bool


class MonthPointOut(BaseModel):
    label: str
    month: int
    year: int
    kwh: float
    daily_kwh: float
    amount_inr: float | None
    estimated_cost: float
    is_anomaly: bool
    anomaly_score: float


class ForecastPointOut(BaseModel):
    label: str
    month: int
    year: int
    kwh: float
    lower: float
    upper: float
    estimated_cost: float


class AdviceCard(BaseModel):
    kind: Literal["ok", "warn", "info"]
    title: str
    body: str


class BillAnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    history: list[MonthPointOut]
    forecast: list[ForecastPointOut]
    model_used: str
    model_scores: dict[str, float]
    trend_pct_per_month: float
    trend_direction: str
    avg_monthly_kwh: float
    avg_monthly_cost: float
    baseload_kwh_per_day: float
    peak_month: str
    low_month: str
    billing_cycle_days: int
    advice: list[AdviceCard]
    optimal_target: dict[str, Any]
    notes: list[str]


class ApplianceChangeIn(BaseModel):
    action: Literal["add", "remove"]
    category: str
    quantity: int = Field(1, ge=1, le=20)
    hours_per_day: float = Field(4, ge=0, le=24)
    specs: dict[str, Any] = Field(default_factory=dict)


class ScenarioRequest(BaseModel):
    changes: list[ApplianceChangeIn] = Field(..., min_length=1, max_length=30)
    baseline_monthly_kwh: float | None = Field(None, ge=0, le=20000)
    baseline_months: list[tuple[str, float]] | None = Field(
        None, description="Optional per-month baseline, e.g. the bill forecast: [['2026-11', 240.5], ...]"
    )


class ChangeImpactOut(BaseModel):
    action: str
    category: str
    label: str
    quantity: int
    hours_per_day: float
    daily_kwh: float
    monthly_kwh: float


class MonthImpactOut(BaseModel):
    label: str
    baseline_kwh: float
    new_kwh: float
    baseline_cost: float
    new_cost: float


class ScenarioResponse(BaseModel):
    baseline_monthly_kwh: float
    new_monthly_kwh: float
    baseline_monthly_cost: float
    new_monthly_cost: float
    delta_monthly_kwh: float
    delta_monthly_cost: float
    delta_pct: float
    changes: list[ChangeImpactOut]
    months: list[MonthImpactOut]
    verdict: str
    tips: list[str]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=30)
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    reply: str
    engine: Literal["claude", "offline"]
    tools_used: list[str] = Field(default_factory=list)
