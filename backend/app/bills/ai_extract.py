"""Vision-model bill reading (optional — requires Anthropic credentials).

Classical OCR handles printed bills well but struggles with handwriting,
skewed phone photos and faded thermal-printer receipts. When a Claude client
is configured, the uploaded image/PDF is also sent to the model with a
strict JSON schema, and its readings replace the regex-parsed ones whenever
they are more complete.
"""
from __future__ import annotations

import base64
import logging

from pydantic import BaseModel, Field

from app.bills.parser import ParsedReading
from app.core.llm import CLAUDE_MODEL, FALLBACK_BODY, FALLBACK_HEADERS, get_client

log = logging.getLogger(__name__)


class _AiReading(BaseModel):
    period_end: str | None = Field(None, description="End date of the billing period / reading date, YYYY-MM-DD")
    period_days: int = Field(..., description="Length of the billing period in days (TNEB bills are usually 60)")
    units_kwh: float | None = Field(None, description="Units (kWh) consumed in this period")
    amount_inr: float | None = Field(None, description="Bill amount in rupees, if shown")
    previous_reading: float | None = None
    current_reading: float | None = None


class _AiExtraction(BaseModel):
    readings: list[_AiReading]
    remarks: str = Field("", description="Anything unclear or illegible")


PROMPT = (
    "This is an Indian household electricity bill, meter-card photo, or a handwritten "
    "log of monthly meter readings. Extract every billing period you can see. For a "
    "single bill return one reading; for a log or a bill that shows a consumption "
    "history table return one reading per period. If only a month is given, use the "
    "last day of that month as period_end. Never guess a number you cannot read — "
    "leave it null and mention it in remarks."
)


def extract_with_ai(data: bytes, media_type: str) -> list[ParsedReading] | None:
    client = get_client()
    if client is None:
        return None

    b64 = base64.standard_b64encode(data).decode("utf-8")
    if media_type == "application/pdf":
        block = {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}}
    else:
        if media_type == "image/jpg":
            media_type = "image/jpeg"
        block = {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}

    try:
        response = client.messages.parse(
            model=CLAUDE_MODEL,
            max_tokens=4000,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": [block, {"type": "text", "text": PROMPT}]}],
            output_format=_AiExtraction,
            extra_headers=FALLBACK_HEADERS,
            extra_body=FALLBACK_BODY,
        )
    except Exception as exc:  # network, auth, unsupported media — fall back to OCR
        log.warning("AI bill extraction failed: %s", exc)
        return None

    if response.stop_reason == "refusal" or response.parsed_output is None:
        return None

    parsed = response.parsed_output
    notes = [parsed.remarks] if parsed.remarks else []
    return [
        ParsedReading(
            period_end=r.period_end,
            period_days=r.period_days or 30,
            units_kwh=r.units_kwh,
            amount_inr=r.amount_inr,
            previous_reading=r.previous_reading,
            current_reading=r.current_reading,
            confidence=0.9 if r.units_kwh is not None else 0.0,
            source="ai_vision",
            notes=list(notes),
        )
        for r in parsed.readings
    ]
