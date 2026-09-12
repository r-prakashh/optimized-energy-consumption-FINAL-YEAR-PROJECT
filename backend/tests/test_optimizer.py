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
