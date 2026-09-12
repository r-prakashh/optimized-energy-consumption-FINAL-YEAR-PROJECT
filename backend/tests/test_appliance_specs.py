from app.core.appliance_specs import compute_effective_watts


def test_higher_star_rating_reduces_ac_wattage():
    watts_3star = compute_effective_watts(
        "air_conditioner", 1500, {"capacity_ton": 1.5, "star_rating": 3, "inverter": False}
    )
    watts_5star = compute_effective_watts(
        "air_conditioner", 1500, {"capacity_ton": 1.5, "star_rating": 5, "inverter": False}
    )
    assert watts_5star < watts_3star


def test_inverter_ac_uses_less_power_than_non_inverter():
    non_inverter = compute_effective_watts(
        "air_conditioner", 1500, {"capacity_ton": 1.5, "star_rating": 3, "inverter": False}
    )
    inverter = compute_effective_watts(
        "air_conditioner", 1500, {"capacity_ton": 1.5, "star_rating": 3, "inverter": True}
    )
    assert inverter < non_inverter


def test_larger_ac_tonnage_uses_more_power():
    small = compute_effective_watts(
        "air_conditioner", 1500, {"capacity_ton": 1.0, "star_rating": 3, "inverter": False}
    )
    large = compute_effective_watts(
        "air_conditioner", 1500, {"capacity_ton": 2.0, "star_rating": 3, "inverter": False}
    )
    assert large > small


def test_empty_specs_falls_back_to_base_watts():
    watts = compute_effective_watts("air_conditioner", 1500, {})
    assert watts == 1500


def test_bldc_fan_uses_far_less_power_than_standard():
    standard = compute_effective_watts("fan", 75, {"motor_type": "standard"})
    bldc = compute_effective_watts("fan", 75, {"motor_type": "bldc_5star"})
    assert bldc < standard / 2


def test_unknown_category_returns_base_watts_unchanged():
    watts = compute_effective_watts("lighting", 60, {"anything": 1})
    assert watts == 60
