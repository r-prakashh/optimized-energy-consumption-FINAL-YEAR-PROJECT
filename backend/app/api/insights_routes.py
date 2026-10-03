"""Endpoints for bill upload/OCR, bill-history analysis, the appliance
add/remove simulator and the Volt assistant."""
from dataclasses import asdict

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.routes import _appliance_model
from app.assistant.chat import chat
from app.bills.ai_extract import extract_with_ai
from app.bills.ocr import OcrUnavailableError, detect_kind, extract_text
from app.bills.parser import parse_bill_text
from app.core.llm import llm_available
from app.ml.bill_trend import BillReading, analyse, generate_advice, optimal_target
from app.optimization.scenario import ApplianceChange, simulate
from app.schemas.bills import (
    BillAnalysisRequest,
    BillAnalysisResponse,
    BillUploadResponse,
    BillUploadResult,
    ChatRequest,
    ChatResponse,
    ScenarioRequest,
    ScenarioResponse,
)

router = APIRouter()

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES = 12


def _process_file(data: bytes, filename: str, content_type: str | None) -> BillUploadResult:
    kind = detect_kind(filename, content_type)
    if kind == "unknown":
        return BillUploadResult(filename=filename, method="none", readings=[], error="Unsupported file type — use PDF, PNG, JPG or WEBP.")

    method, confidence, preview, readings = "none", None, "", []
    ocr_error = None
    try:
        ocr = extract_text(data, filename, content_type)
        method, confidence, preview = ocr.method, ocr.confidence, ocr.text[:1500]
        readings = parse_bill_text(ocr.text, source=ocr.method)
    except OcrUnavailableError as exc:
        ocr_error = str(exc)
    except Exception as exc:  # corrupt PDF, unreadable image
        ocr_error = f"Couldn't read this file: {exc}"

    # Vision-model pass when OCR left gaps (handwriting, poor photos) —
    # or always, if it's configured and the OCR path found nothing.
    incomplete = not readings or any(r.units_kwh is None or r.period_end is None for r in readings)
    if incomplete and llm_available():
        media = "application/pdf" if kind == "pdf" else (content_type or "image/jpeg")
        ai = extract_with_ai(data, media)
        if ai and sum(r.units_kwh is not None for r in ai) >= sum(r.units_kwh is not None for r in readings):
            readings, method = ai, "ai_vision"
            ocr_error = None

    return BillUploadResult(
        filename=filename,
        method=method,
        ocr_confidence=confidence,
        readings=[r.to_dict() for r in readings],
        raw_text_preview=preview,
        error=ocr_error if not readings else None,
    )


@router.post("/bills/upload", response_model=BillUploadResponse)
async def upload_bills(files: list[UploadFile] = File(...)):
    """OCR one or more past bills (PDF / photo / handwritten log) into
    editable readings. Nothing is stored server-side."""
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Upload at most {MAX_FILES} files at a time.")
    results = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_FILE_BYTES:
            results.append(BillUploadResult(filename=f.filename or "file", method="none", readings=[], error="File larger than 10 MB."))
            continue
        results.append(await run_in_threadpool(_process_file, data, f.filename or "file", f.content_type))
    return BillUploadResponse(files=results, ai_vision_used=any(r.method == "ai_vision" for r in results))


@router.post("/bills/analyze", response_model=BillAnalysisResponse)
def analyze_bills(payload: BillAnalysisRequest):
    """Trend, anomalies, N-month forecast (model chosen by backtest) and advice."""
    readings = [
        BillReading(r.period_end, r.period_days, r.units_kwh, r.amount_inr) for r in payload.readings
    ]
    try:
        a = analyse(readings, payload.horizon_months)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    base_for_target = a.forecast[0].kwh if a.forecast else a.avg_monthly_kwh
    return BillAnalysisResponse(
        history=[asdict(p) for p in a.history],
        forecast=[asdict(p) for p in a.forecast],
        model_used=a.model_used,
        model_scores=a.model_scores,
        trend_pct_per_month=a.trend_pct_per_month,
        trend_direction=a.trend_direction,
        avg_monthly_kwh=a.avg_monthly_kwh,
        avg_monthly_cost=a.avg_monthly_cost,
        baseload_kwh_per_day=a.baseload_kwh_per_day,
        peak_month=a.peak_month,
        low_month=a.low_month,
        billing_cycle_days=a.billing_cycle_days,
        advice=generate_advice(a),
        optimal_target=optimal_target(base_for_target),
        notes=a.notes,
    )


@router.post("/scenario", response_model=ScenarioResponse)
def appliance_scenario(payload: ScenarioRequest):
    """Monthly kWh / bill impact of adding or removing appliances."""
    changes = [ApplianceChange(c.action, c.category, c.quantity, c.hours_per_day, c.specs) for c in payload.changes]
    try:
        r = simulate(
            changes,
            _appliance_model,
            baseline_monthly_kwh=payload.baseline_monthly_kwh,
            baseline_months=payload.baseline_months,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return ScenarioResponse(**asdict(r))


@router.post("/chat", response_model=ChatResponse)
async def assistant_chat(payload: ChatRequest):
    if payload.messages[-1].role != "user":
        raise HTTPException(400, "The last message must be from the user.")
    msgs = [m.model_dump() for m in payload.messages]
    return await run_in_threadpool(chat, msgs, payload.context, _appliance_model)


@router.get("/assistant/status")
def assistant_status():
    return {"llm_enabled": llm_available()}
