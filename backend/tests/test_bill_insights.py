from datetime import date

import pytest

from app.assistant.chat import _offline_reply
from app.bills.parser import parse_bill_text
from app.core.config import estimate_cost
from app.ml.bill_trend import BillReading, analyse, generate_advice, normalise_to_months, optimal_target
from app.ml.models.appliance_model import ApplianceModel
from app.optimization.scenario import ApplianceChange, simulate

TNEB_BILL_TEXT = """
TAMIL NADU POWER DISTRIBUTION CORPORATION (TNPDCL)
Service No: 01-234-567   Tariff: LA1A  Bi-monthly
Assessment Date : 14-03-2026
Previous Reading : 12450   Present Reading : 12812
Units Consumed : 362
Net Amount Payable : Rs. 1,186.00
Previous Assessment Date 13-01-2026
"""

HANDWRITTEN_LOG = """
Jan 2026 - 210 units  Rs 520
Feb 2026 - 198 units  Rs 470
Mar 2026 - 245 units  Rs 690
Apr 2026 - 302 units  Rs 1040
"""


def test_parses_tneb_bill_fields():
    [r] = parse_bill_text(TNEB_BILL_TEXT)
    assert r.units_kwh == 362
    assert r.amount_inr == 1186.0
    assert r.period_end == "2026-03-14"
    assert r.period_days == 60  # two assessment dates ~60 days apart
    assert r.confidence >= 0.9


def test_meter_difference_overrides_misread_units():
    text = TNEB_BILL_TEXT.replace("Units Consumed : 362", "Units Consumed : 862")
    [r] = parse_bill_text(text)
    assert r.units_kwh == 362
    assert any("meter difference" in n for n in r.notes)


def test_parses_handwritten_multi_month_log():
    readings = parse_bill_text(HANDWRITTEN_LOG)
    assert [r.units_kwh for r in readings] == [210, 198, 245, 302]
    assert readings[0].period_end == "2026-01-31"
    assert readings[2].amount_inr == 690


def test_bimonthly_bill_spreads_over_two_months():
    pts = normalise_to_months([BillReading(date(2026, 3, 31), 59, 360)])
    assert [p.label for p in pts] == ["2026-02", "2026-03"]
    assert sum(p.daily_kwh for p in pts) / 2 == pytest.approx(360 / 59, rel=0.01)


def _monthly(values, start_year=2025, start_month=1):
    out = []
    y, m = start_year, start_month
    for v in values:
        nxt_y, nxt_m = (y + (m == 12), m % 12 + 1)
        end = date.fromordinal(date(nxt_y, nxt_m, 1).toordinal() - 1)
        out.append(BillReading(end, end.day, v))  # one full calendar month per bill
        y, m = nxt_y, nxt_m
    return out


def test_rising_trend_detected_and_forecast_positive():
    readings = _monthly([180, 190, 205, 240, 270, 255, 240, 245, 250, 245, 235, 240])
    a = analyse(readings, horizon_months=3)
    assert len(a.history) == 12
    assert len(a.forecast) == 3
    assert a.model_used in a.model_scores
    assert all(f.lower <= f.kwh <= f.upper for f in a.forecast)
    assert a.trend_direction == "rising"


def test_anomaly_flagged():
    readings = _monthly([200, 205, 198, 520, 210, 202, 199, 204])
    a = analyse(readings)
    flagged = [p.label for p in a.history if p.is_anomaly]
    assert flagged == ["2025-04"]
    assert any("unusually high" in t["title"] for t in generate_advice(a))


def test_optimal_target_uses_slab_boundary_when_close():
    t = optimal_target(215)
    assert t["target_monthly_kwh"] == 200
    assert t["monthly_saving_inr"] == pytest.approx(estimate_cost(215, 30) - estimate_cost(200, 30), abs=0.01)


def test_scenario_add_and_remove():
    model = ApplianceModel()
    add = simulate([ApplianceChange("add", "air_conditioner", 1, 6, {"capacity_ton": 1.5, "star_rating": 3, "inverter": False})], model, baseline_monthly_kwh=200)
    assert add.new_monthly_kwh > 200
    assert add.delta_monthly_cost > 0
    remove = simulate([ApplianceChange("remove", "water_heater", 1, 1)], model, baseline_monthly_kwh=200)
    assert remove.new_monthly_kwh < 200
    assert remove.delta_monthly_cost < 0


def test_scenario_never_goes_negative():
    r = simulate([ApplianceChange("remove", "air_conditioner", 3, 12)], ApplianceModel(), baseline_monthly_kwh=50)
    assert r.new_monthly_kwh == 0


def test_offline_assistant_answers_what_if():
    reply = _offline_reply([{"role": "user", "content": "What if I add a 1.5 ton AC for 6 hours?"}], {}, ApplianceModel())
    assert "Air Conditioner" in reply and "₹" in reply


def test_offline_assistant_cost_question():
    reply = _offline_reply([{"role": "user", "content": "How much will 300 units cost?"}], {}, ApplianceModel())
    assert f"{estimate_cost(300, 30):.0f}" in reply


def test_offline_assistant_quantity_ignores_spec_numbers():
    reply = _offline_reply(
        [{"role": "user", "content": "What if I add two 1.5 ton 5 star inverter AC for 8 hours?"}], {}, ApplianceModel()
    )
    assert reply.startswith("2× Air Conditioner (8 h/day)")


def test_ocr_reads_rendered_bill_image():
    pytest.importorskip("rapidocr_onnxruntime")
    import io

    from PIL import Image, ImageDraw, ImageFont

    from app.bills.ocr import extract_text

    img = Image.new("RGB", (1100, 300), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except OSError:
        font = ImageFont.load_default()
    for i, line in enumerate(["Assessment Date : 14-03-2026", "Units Consumed : 362", "Net Amount Payable : Rs. 1186.00"]):
        draw.text((40, 30 + i * 70), line, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    ocr = extract_text(buf.getvalue(), "bill.png", "image/png")
    [r] = parse_bill_text(ocr.text, ocr.method)
    assert r.units_kwh == 362
    assert r.amount_inr == 1186.0
