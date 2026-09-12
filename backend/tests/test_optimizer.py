from app.ml.models.appliance_model import ApplianceModel
from app.optimization.optimizer import ApplianceUsage, optimize


def test_no_reduction_needed_when_within_budget():
    model = ApplianceModel()
    usages = [ApplianceUsage("lighting", 4)]
    result = optimize(usages, duration_days=30, budget=1_000_000, appliance_model=model)
    assert result.budget_met
    assert result.appliances[0].recommended_hours == 4


def test_reduces_flexible_appliance_before_essential():
    model = ApplianceModel()
    usages = [
        ApplianceUsage("air_conditioner", 8),
        ApplianceUsage("refrigerator", 24),
    ]
    # A tight budget forces reduction; AC (high flexibility) should be cut
    # before refrigerator (flexibility 'none', min_hours 24).
    result = optimize(usages, duration_days=30, budget=500, appliance_model=model)

    ac_result = next(a for a in result.appliances if a.category == "air_conditioner")
    fridge_result = next(a for a in result.appliances if a.category == "refrigerator")

    assert ac_result.recommended_hours < 8
    assert fridge_result.recommended_hours == 24  # essential load untouched


def test_respects_minimum_hours_even_if_budget_unmet():
    model = ApplianceModel()
    usages = [ApplianceUsage("refrigerator", 24)]
    result = optimize(usages, duration_days=30, budget=1, appliance_model=model)
    # Refrigerator has flexibility 'none' / min_hours 24 -> cannot be reduced
    assert result.appliances[0].recommended_hours == 24
    assert not result.budget_met


def test_tod_shift_opportunity_flagged_for_shiftable_appliance():
    model = ApplianceModel()
    # Usage high enough to land in a paid TNEB slab (not the 0-100 free tier)
    # so shifting actually has a non-zero rate to save against.
    usages = [ApplianceUsage("washing_machine", 1), ApplianceUsage("air_conditioner", 6)]
    result = optimize(usages, duration_days=30, budget=1_000_000, appliance_model=model)

    # washing_machine is marked shiftable in the catalog -> should surface a
    # ToD shift opportunity; air_conditioner is not shiftable (thermal
    # comfort load) -> should not, even though it's the larger consumer.
    shifted_categories = {o.category for o in result.tod_shift_opportunities}
    assert "washing_machine" in shifted_categories
    assert "air_conditioner" not in shifted_categories
    assert result.tod_total_saving > 0

    # Regression guard: a per-appliance DAILY saving can never legitimately
    # exceed that appliance's own DAILY energy cost share of the total bill
    # (a unit-scale bug here previously mixed period cost with daily kWh,
    # producing a >10x-inflated "average rate" and absurd savings figures).
    washing_machine_kwh = next(
        o.daily_kwh for o in result.tod_shift_opportunities if o.category == "washing_machine"
    )
    naive_daily_rate_ceiling = result.original_cost / result.duration_days / result.projected_daily_kwh
    saving_per_kwh = next(
        o.estimated_saving for o in result.tod_shift_opportunities if o.category == "washing_machine"
    ) / washing_machine_kwh
    assert saving_per_kwh < naive_daily_rate_ceiling


def test_non_shiftable_essential_appliance_has_no_tod_opportunity():
    model = ApplianceModel()
    usages = [ApplianceUsage("refrigerator", 24)]
    result = optimize(usages, duration_days=30, budget=1_000_000, appliance_model=model)
    assert result.tod_shift_opportunities == []
    assert result.tod_total_saving == 0
