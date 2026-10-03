"""Turns raw OCR / PDF text from an electricity bill into structured readings.

Two input shapes are handled:

* **A single bill** (TNEB/TANGEDCO e-bill, printed card, photo of a bill):
  looks for labelled fields — units consumed, previous/present meter
  reading, bill amount, bill/reading date — using tolerant regexes, because
  OCR output mangles spacing, punctuation and casing.
* **A handwritten or typed log** of several months ("Jan 2025 - 245 units -
  Rs 980"): every line that carries a month name + a number becomes its own
  reading.

Every value comes back with a confidence score and the UI shows them in an
editable table, so a misread digit is corrected by the user rather than
silently corrupting the trend analysis.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
MONTH_RE = r"(jan|feb|mar|apr|may|jun|jul|aug|sept?|oct|nov|dec)[a-z]*\.?"

NUM = r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?"

UNITS_PATTERNS = [
    rf"(?:units?\s*consumed|consumption|consumed\s*units?|total\s*units?|net\s*units?|units?\s*used|energy\s*consumed)\s*(?:\(?\s*kwh\s*\)?)?\s*[:\-=]?\s*{NUM}",
    rf"{NUM}\s*(?:kwh|units?)\b",
]
AMOUNT_PATTERNS = [
    rf"(?:net\s*amount|bill\s*amount|amount\s*payable|total\s*amount|amount\s*due|cc\s*charges|current\s*charges|amount)\s*(?:\(?\s*(?:rs|inr|₹)\.?\s*\)?)?\s*[:\-=]?\s*(?:rs\.?|inr|₹)?\s*{NUM}",
    rf"(?:rs\.?|inr|₹)\s*{NUM}",
]
PREV_READING = rf"(?:previous|prev\.?|old|last)\s*(?:meter\s*)?reading\s*[:\-=]?\s*{NUM}"
CURR_READING = rf"(?:present|current|curr\.?|new|final)\s*(?:meter\s*)?reading\s*[:\-=]?\s*{NUM}"
DATE_NUMERIC = r"\b(\d{1,2})[\-/.](\d{1,2})[\-/.](\d{2,4})\b"
DATE_TEXT = rf"\b(\d{{1,2}})?\s*{MONTH_RE}[\s,\-/']*(\d{{2,4}})\b"

TNEB_MARKERS = ("tneb", "tangedco", "tnpdcl", "tamil nadu", "tamilnadu", "bi-monthly", "bimonthly")


@dataclass
class ParsedReading:
    period_end: str | None          # ISO date — end of the billing period
    period_days: int                # length of the billing period
    units_kwh: float | None
    amount_inr: float | None = None
    previous_reading: float | None = None
    current_reading: float | None = None
    confidence: float = 0.0         # 0-1, how sure the parser is about units_kwh
    source: str = "ocr"             # "ocr" | "pdf_text_layer" | "ai_vision" | "manual"
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _to_float(whole: str, frac: str | None) -> float:
    value = float(whole.replace(",", ""))
    if frac:
        value += float(f"0.{frac}")
    return value


def _normalise(text: str) -> str:
    text = text.replace("₹", "₹").replace("|", " ")
    # Common OCR digit confusions inside numbers: O->0, l/I->1 when flanked by digits.
    text = re.sub(r"(?<=\d)[Oo](?=\d)", "0", text)
    text = re.sub(r"(?<=\d)[lI](?=\d)", "1", text)
    return text


def _year(y: str) -> int:
    n = int(y)
    return n + 2000 if n < 100 else n


def _parse_dates(text: str) -> list[date]:
    found: list[date] = []
    for d, m, y in re.findall(DATE_NUMERIC, text):
        try:
            found.append(date(_year(y), int(m), int(d)))
        except ValueError:
            continue
    for d, mon, y in re.findall(DATE_TEXT, text, flags=re.IGNORECASE):
        month = MONTHS.get(mon.lower()[:4] if mon.lower().startswith("sept") else mon.lower()[:3])
        if not month:
            continue
        try:
            found.append(date(_year(y), month, int(d) if d else 28))
        except ValueError:
            continue
    today = date.today()
    return [d for d in found if date(2000, 1, 1) <= d <= today + timedelta(days=60)]


def _first_number(patterns: list[str], text: str, lo: float, hi: float) -> tuple[float | None, int]:
    """Returns (value, index_of_pattern_that_matched) — earlier patterns are
    the labelled ones and earn higher confidence."""
    for idx, pattern in enumerate(patterns):
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            groups = [g for g in match.groups()]
            value = _to_float(groups[-2], groups[-1])
            if lo <= value <= hi:
                return value, idx
    return None, -1


def _default_period_days(text_lower: str) -> int:
    return 60 if any(m in text_lower for m in TNEB_MARKERS) else 30


def parse_multi_month_log(text: str) -> list[ParsedReading]:
    """Handwritten/typed logs: one reading per line that has month + number."""
    readings: list[ParsedReading] = []
    line_re = re.compile(rf"{MONTH_RE}[\s,\-/']*(\d{{2,4}})?", re.IGNORECASE)
    for raw in text.splitlines():
        line = raw.strip()
        m = line_re.search(line)
        if not m:
            continue
        rest = line[m.end():]
        units, _ = _first_number(UNITS_PATTERNS, rest, 1, 20000)
        if units is None:
            # bare "Jan 2025 245" — first standalone number after the month
            bare = re.search(r"\b(\d{2,5})(?:\.\d+)?\b", rest)
            units = float(bare.group(1)) if bare else None
        if units is None:
            continue
        amount, _ = _first_number(AMOUNT_PATTERNS, rest, 1, 500000)
        mon = m.group(1).lower()
        month = MONTHS.get(mon[:3]) or 1
        year = _year(m.group(2)) if m.group(2) else date.today().year
        # A log line names a month; treat its end as the reading date.
        nxt = date(year + (month == 12), month % 12 + 1, 1)
        readings.append(
            ParsedReading(
                period_end=(nxt - timedelta(days=1)).isoformat(),
                period_days=30,
                units_kwh=units,
                amount_inr=amount if amount != units else None,
                confidence=0.6,
                notes=[f"Parsed from line: '{line[:60]}'"],
            )
        )
    return readings


def parse_single_bill(text: str, source: str = "ocr") -> ParsedReading:
    text_lower = text.lower()
    notes: list[str] = []

    prev_r, _ = _first_number([PREV_READING], text, 0, 10_000_000)
    curr_r, _ = _first_number([CURR_READING], text, 0, 10_000_000)
    units, units_idx = _first_number(UNITS_PATTERNS, text, 1, 20000)
    confidence = {0: 0.9, 1: 0.55}.get(units_idx, 0.0)

    if prev_r is not None and curr_r is not None and curr_r > prev_r:
        diff = curr_r - prev_r
        if units is None or abs(diff - units) / max(units, 1) > 0.05:
            if units is not None:
                notes.append(f"Units field ({units:g}) differs from meter difference ({diff:g}); using meter difference.")
            units = diff
        confidence = 0.95

    amount, _ = _first_number(AMOUNT_PATTERNS, text, 1, 500000)
    if amount is not None and units is not None and amount == units:
        amount = None

    period_days = _default_period_days(text_lower)
    dates = sorted(set(_parse_dates(text)))
    period_end = None
    if dates:
        period_end = dates[-1].isoformat()
        if len(dates) >= 2:
            span = (dates[-1] - dates[-2]).days
            if 20 <= span <= 70:
                period_days = span
    else:
        notes.append("No bill date found — please set the billing month.")

    if units is None:
        notes.append("Couldn't find units consumed — please type it in.")

    return ParsedReading(
        period_end=period_end,
        period_days=period_days,
        units_kwh=units,
        amount_inr=amount,
        previous_reading=prev_r,
        current_reading=curr_r,
        confidence=round(confidence, 2),
        source=source,
        notes=notes,
    )


def parse_bill_text(text: str, source: str = "ocr") -> list[ParsedReading]:
    text = _normalise(text)
    multi = parse_multi_month_log(text)
    # A log with 2+ month lines and no "units consumed" label is treated as a
    # history table; otherwise it's one bill (whose dates also contain months).
    has_bill_labels = re.search(r"units?\s*consumed|meter\s*reading|amount\s*payable|net\s*amount", text, re.IGNORECASE)
    if len(multi) >= 2 and not has_bill_labels:
        for r in multi:
            r.source = source
        return multi
    return [parse_single_bill(text, source)]


def parse_iso(d: str) -> date:
    return datetime.fromisoformat(d).date()
