"""Infer which appliance category each REFIT `Appliance<N>` channel likely
represents, from the channel's own consumption signature.

REFIT's official per-house channel legend (which channel number is which
physical device) isn't bundled with this dataset drop. Rather than guess
labels from memory (risking silently wrong training data), this module
classifies each channel from measurable behaviour:

  - duty_cycle:       fraction of readings above an "on" threshold
  - mean_power_on:    average power while on (W)
  - evening_share:    fraction of "on" time falling in 18:00-23:00
  - daytime_share:    fraction of "on" time falling in 09:00-17:00

This is a heuristic, not ground truth. It is the standard fallback approach
in non-intrusive load monitoring (NILM) work when explicit channel metadata
is unavailable: identify appliance type from its own load signature rather
than an external label.

RESULT OF RUNNING THIS ON HOUSES 1-5: the label distribution was implausible
(most channels classified as "washing_machine"/"lighting", multiple houses
with zero detected refrigerators) and max-power readings showed 2-3.5kW
spikes even on channels otherwise behaving like low-power circuits —
consistent with sensor noise/cross-talk in this particular dataset drop
rather than a real signature. Confidence was too low to trust as training
labels, so its output is NOT wired into build_dataset.py's
HOUSE_APPLIANCE_MAP. The appliance-level model deliberately falls back to
nameplate-wattage arithmetic instead (see app/ml/models/appliance_model.py)
until a verified REFIT channel legend is available. Kept here as a
documented, runnable experiment rather than deleted.
"""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ON_THRESHOLD_WATTS = 8.0  # REFIT channels read ~0-3W standby noise; 8W clears that


@dataclass
class ChannelSignature:
    house_id: int
    column: str
    duty_cycle: float
    mean_power_on: float
    max_power: float
    evening_share: float
    daytime_share: float


def compute_signature(house_id: int, column: str, df: pd.DataFrame) -> ChannelSignature | None:
    series = df[column].fillna(0)
    on_mask = series > ON_THRESHOLD_WATTS
    if on_mask.sum() < 50:  # channel essentially never used — not classifiable
        return None

    hours = df["Time"].dt.hour
    evening_mask = on_mask & hours.between(18, 23)
    daytime_mask = on_mask & hours.between(9, 17)

    return ChannelSignature(
        house_id=house_id,
        column=column,
        duty_cycle=float(on_mask.mean()),
        mean_power_on=float(series[on_mask].mean()),
        max_power=float(series.max()),
        evening_share=float(evening_mask.sum() / max(on_mask.sum(), 1)),
        daytime_share=float(daytime_mask.sum() / max(on_mask.sum(), 1)),
    )


def classify(sig: ChannelSignature) -> str | None:
    """
    Rule-based classification, applied in priority order (most distinctive
    signature first). Returns None ("unclassified") rather than forcing a
    guess when no rule confidently matches — an unmapped channel is simply
    excluded from appliance-model training instead of poisoning it.
    """
    # Always-on, low power, near-constant duty cycle -> compressor-cycled load
    if sig.duty_cycle > 0.85 and sig.mean_power_on < 250:
        return "refrigerator"

    # High peak power, used only briefly and rarely -> washing machine class
    if sig.max_power > 1200 and sig.duty_cycle < 0.15 and sig.mean_power_on > 300:
        return "washing_machine"

    # High peak, extremely brief, low duty cycle, high mean-when-on -> microwave
    if sig.max_power > 900 and sig.duty_cycle < 0.03 and sig.mean_power_on > 500:
        return "microwave"

    # Moderate power, evening-concentrated -> television
    if 40 <= sig.mean_power_on <= 250 and sig.evening_share > 0.5 and sig.duty_cycle < 0.5:
        return "television"

    # Moderate power, daytime-concentrated, longer duty cycle -> computer
    if 40 <= sig.mean_power_on <= 300 and sig.daytime_share > 0.5 and sig.duty_cycle < 0.6:
        return "computer"

    # Low power, broad time-of-day spread, moderate duty cycle -> lighting
    if sig.mean_power_on <= 80 and 0.1 < sig.duty_cycle < 0.6:
        return "lighting"

    return None


def build_house_appliance_map(
    raw_dir: Path, house_ids: list[int]
) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    for house_id in house_ids:
        path = raw_dir / f"House_{house_id}_clean.csv"
        if not path.exists():
            continue
        columns = [f"Appliance{i}" for i in range(1, 10)]
        df = pd.read_csv(path, usecols=["Time", *columns], parse_dates=["Time"])

        house_map = {}
        for column in columns:
            sig = compute_signature(house_id, column, df)
            if sig is None:
                continue
            category = classify(sig)
            if category is not None:
                house_map[column] = category

        if house_map:
            result[house_id] = house_map
        print(f"House {house_id}: {house_map}")

    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--houses", type=str, required=True)
    args = parser.parse_args()
    house_ids = [int(h) for h in args.houses.split(",")]

    raw_dir = (
        Path(__file__).resolve().parents[4]
        / "data" / "raw" / "AI_Energy_Project" / "REFIT_CLEAN"
    )
    mapping = build_house_appliance_map(raw_dir, house_ids)
    print("\nHOUSE_APPLIANCE_MAP =", mapping)
