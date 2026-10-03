"""Reproduces the project-report figures (Chapter 5) from the real models.

    cd backend
    python -m experiments.report_figures

Writes PNGs + a metrics JSON to ../docs/figures/. Reporting-only — nothing
here is used by the deployed API.

Fig. 5.4  Model performance comparison (held-out REFIT house-days)
Fig. 5.5  Actual vs predicted daily household consumption (LightGBM)
Fig. 5.7  Appliance-level energy consumption distribution (typical TN home)
Fig. 5.8  Budget vs projected cost before and after optimization
"""
try:  # load ONNX runtime's DLLs before LightGBM's OpenMP (see app/main.py)
    import onnxruntime  # noqa: F401
except ImportError:
    pass

import json
from pathlib import Path

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.dates  # noqa: E402,F401
import matplotlib.ticker  # noqa: E402,F401
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.linear_model import LinearRegression  # noqa: E402

import app.ml.models.appliance_model as appliance_module  # noqa: E402
from app.core.config import APPLIANCE_CATALOG  # noqa: E402
from app.ml.models.household_forecaster import (  # noqa: E402
    FEATURE_COLUMNS,
    MODEL_DIR,
    TARGET_COLUMN,
    _chronological_split_per_house,
)
from app.optimization.optimizer import ApplianceUsage, optimize  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "figures"
DATA = ROOT / "data" / "processed" / "household_daily.parquet"

# Palette (validated categorical slots, light mode) + neutrals
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GRAY, GRAY_LIGHT, INK, INK_2, GRID = "#8a8f98", "#c9ccd1", "#1f2328", "#57606a", "#e6e8eb"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": GRAY_LIGHT,
    "axes.labelcolor": INK_2,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "legend.frameon": False,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})


def metrics(y, p):
    y, p = np.asarray(y), np.asarray(p)
    return {
        "MAE": float(np.mean(np.abs(y - p))),
        "RMSE": float(np.sqrt(np.mean((y - p) ** 2))),
        "WMAPE": float(np.sum(np.abs(y - p)) / np.sum(np.abs(y)) * 100),
    }


# ----------------------------------------------------------------- 5.4 / 5.5

def forecasting_figures():
    df = pd.read_parquet(DATA).dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN])
    train, test = _chronological_split_per_house(df)
    Xtr, ytr, Xte, yte = train[FEATURE_COLUMNS], train[TARGET_COLUMN], test[FEATURE_COLUMNS], test[TARGET_COLUMN]

    booster = lgb.Booster(model_file=str(MODEL_DIR / "household_forecaster.txt"))
    preds = {
        "Naive (yesterday)": test["lag_1d"].values,
        "Seasonal naive (last week)": test["lag_7d"].values,
        "7-day moving average": test["rolling_mean_7d"].values,
        "Linear regression": LinearRegression().fit(Xtr, ytr).predict(Xte),
        "Random forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=42, n_jobs=-1)
        .fit(Xtr, ytr).predict(Xte),
        "LightGBM (deployed)": booster.predict(Xte),
    }
    results = {name: metrics(yte, p) for name, p in preds.items()}

    # Fig 5.4 — small multiples, one panel per metric (different units → never one shared axis)
    order = sorted(results, key=lambda n: results[n]["WMAPE"], reverse=True)
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for ax, (key, unit) in zip(axes, [("MAE", "kWh/day"), ("RMSE", "kWh/day"), ("WMAPE", "%")]):
        vals = [results[n][key] for n in order]
        colors = [BLUE if "LightGBM" in n else GRAY_LIGHT for n in order]
        bars = ax.barh(order, vals, color=colors, height=0.62, edgecolor="white", linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(v + max(vals) * 0.02, b.get_y() + b.get_height() / 2, f"{v:.2f}" if unit != "%" else f"{v:.1f}%",
                    va="center", fontsize=8.5, color=INK)
        ax.set_title(f"{key} ({unit})", loc="left")
        ax.set_xlim(0, max(vals) * 1.22)
        ax.grid(axis="y", visible=False)
        ax.tick_params(axis="y", length=0)
    fig.suptitle("Day-ahead household forecasting on held-out REFIT house-days (n = %d) — lower is better" % len(yte),
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold", color=INK)
    fig.tight_layout()
    fig.savefig(OUT / "fig_5_4_model_performance.png")
    plt.close(fig)

    # Fig 5.5 — time series for one house + parity scatter across all houses
    test = test.assign(pred=preds["LightGBM (deployed)"])
    house = 1
    h = test[test.house_id == house].sort_values("date").set_index("date")
    # Reindex to every calendar day so missing REFIT days show as gaps, not bridged lines.
    h = h.reindex(pd.date_range(h.index.min(), h.index.max(), freq="D")).rename_axis("date").reset_index()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [2.3, 1]})
    ax1.plot(h["date"], h[TARGET_COLUMN], color=GRAY, linewidth=1.6, label="Actual")
    ax1.plot(h["date"], h["pred"], color=BLUE, linewidth=2, label="Predicted (LightGBM)")
    ax1.set_title(f"(a) REFIT house {house}, held-out period", loc="left")
    ax1.set_ylabel("Daily consumption (kWh)")
    ax1.legend(loc="upper left", ncol=2)
    ax1.xaxis.set_major_locator(matplotlib.dates.MonthLocator())
    ax1.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b %Y"))

    lim = float(max(test[TARGET_COLUMN].max(), test["pred"].max())) * 1.05
    ax2.scatter(test[TARGET_COLUMN], test["pred"], s=12, color=BLUE, alpha=0.45, edgecolors="white", linewidths=0.4)
    ax2.plot([0, lim], [0, lim], color=INK_2, linestyle="--", linewidth=1)
    ax2.text(lim * 0.97, lim * 0.9, "perfect forecast", ha="right", fontsize=8, color=INK_2)
    ax2.set_xlim(0, lim)
    ax2.set_ylim(0, lim)
    ax2.set_xlabel("Actual (kWh/day)")
    ax2.set_ylabel("Predicted (kWh/day)")
    r = results["LightGBM (deployed)"]
    ax2.set_title(f"(b) All houses · MAE {r['MAE']:.2f} · WMAPE {r['WMAPE']:.1f}%", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_5_5_actual_vs_predicted.png")
    plt.close(fig)

    house_metrics = {
        int(hid): metrics(g[TARGET_COLUMN], g["pred"]) for hid, g in test.groupby("house_id")
    }
    return {"n_train": len(ytr), "n_test": len(yte), "models": results, "lightgbm_by_house": house_metrics}


# ----------------------------------------------------------------- 5.7 / 5.8

REFERENCE_TEMP_C = 30.0  # Chennai annual-average-ish daytime temperature, fixed so figures are reproducible

TYPICAL_TN_HOME = [
    ApplianceUsage("air_conditioner", 7, {"capacity_ton": 1.5, "star_rating": 3, "inverter": True}),
    ApplianceUsage("refrigerator", 24, {"capacity_liters": 250, "star_rating": 3}),
    ApplianceUsage("fan", 14, {"motor_type": "standard"}),
    ApplianceUsage("lighting", 6),
    ApplianceUsage("television", 5, {"screen_size_inches": 43}),
    ApplianceUsage("water_heater", 0.5, {"capacity_liters": 15}),
    ApplianceUsage("motor_pump", 0.5),
    ApplianceUsage("washing_machine", 1, {"capacity_kg": 7, "load_type": "top_load"}),
    ApplianceUsage("computer", 4),
    ApplianceUsage("microwave", 0.3),
]

SCENARIOS = [
    ("Small flat\n(2 fans, TV, fridge)", [
        ApplianceUsage("fan", 16), ApplianceUsage("lighting", 6), ApplianceUsage("television", 6),
        ApplianceUsage("refrigerator", 24), ApplianceUsage("motor_pump", 1)], 380),
    ("1-AC family home", TYPICAL_TN_HOME[:6] + [ApplianceUsage("washing_machine", 1)], 3000),
    ("Work-from-home\n(AC + PC all day)", [
        ApplianceUsage("air_conditioner", 10, {"capacity_ton": 1.5, "star_rating": 3, "inverter": False}),
        ApplianceUsage("computer", 10), ApplianceUsage("fan", 12), ApplianceUsage("lighting", 6),
        ApplianceUsage("refrigerator", 24), ApplianceUsage("microwave", 0.5)], 5500),
    ("Large home\n(2-ton AC, geyser)", [
        ApplianceUsage("air_conditioner", 12, {"capacity_ton": 2.0, "star_rating": 3, "inverter": False}),
        ApplianceUsage("water_heater", 2, {"capacity_liters": 25}), ApplianceUsage("fan", 18),
        ApplianceUsage("lighting", 10), ApplianceUsage("television", 8, {"screen_size_inches": 55}),
        ApplianceUsage("refrigerator", 24, {"capacity_liters": 450, "star_rating": 3}),
        ApplianceUsage("motor_pump", 1.5), ApplianceUsage("washing_machine", 2)], 10500),
]


def appliance_figures():
    appliance_module.get_cached_tn_temperature = lambda city="chennai": REFERENCE_TEMP_C
    model = appliance_module.ApplianceModel()

    # Fig 5.7
    rows = []
    for u in TYPICAL_TN_HOME:
        kwh_day = np.mean([model.estimate_kwh(u.category, u.hours_per_day, d, u.specs) for d in range(7)])
        rows.append((APPLIANCE_CATALOG[u.category]["label"], u.hours_per_day, kwh_day * 30))
    rows.sort(key=lambda r: r[2])
    total = sum(r[2] for r in rows)
    fig, ax = plt.subplots(figsize=(9, 4.4))
    labels = [f"{r[0]}  ({r[1]:g} h/day)" for r in rows]
    vals = [r[2] for r in rows]
    colors = [BLUE if v == max(vals) else "#86b6ef" for v in vals]
    bars = ax.barh(labels, vals, color=colors, height=0.66, edgecolor="white", linewidth=2)
    for b, v in zip(bars, vals):
        ax.text(v + total * 0.006, b.get_y() + b.get_height() / 2, f"{v:.0f} kWh  ·  {v / total * 100:.0f}%",
                va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, max(vals) * 1.3)
    ax.set_xlabel("Energy per month (kWh)")
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    ax.set_title(f"Typical Tamil Nadu household — {total:.0f} kWh/month, at {REFERENCE_TEMP_C:.0f} °C", loc="left")
    fig.tight_layout()
    fig.savefig(OUT / "fig_5_7_appliance_distribution.png")
    plt.close(fig)
    appliance_table = [{"appliance": r[0], "hours_per_day": r[1], "kwh_month": round(r[2], 1),
                        "share_pct": round(r[2] / total * 100, 1)} for r in reversed(rows)]

    # Fig 5.8
    out = []
    for name, usages, budget in SCENARIOS:
        r = optimize(usages, duration_days=30, budget=budget, appliance_model=model)
        out.append({"scenario": name.replace("\n", " "), "budget": budget, "before": r.original_cost,
                    "after": r.projected_cost, "budget_met": r.budget_met,
                    "kwh_before": round(sum(model.estimate_kwh(u.category, u.hours_per_day, 0, u.specs) for u in usages) * 30, 1),
                    "kwh_after": r.projected_total_kwh})
    # One panel per household (own ₹ scale) so the small flat isn't flattened by the large home.
    fig, axes = plt.subplots(1, len(out), figsize=(11.5, 4.2))
    for ax, o, (title, _, _) in zip(axes, out, SCENARIOS):
        vals = [o["before"], o["after"]]
        bars = ax.bar([0, 1], vals, width=0.62, color=[GRAY_LIGHT, BLUE], edgecolor="white", linewidth=2)
        ax.axhline(o["budget"], color=ORANGE, linewidth=2.2)
        top = max(vals) * 1.22
        ax.set_ylim(0, top)
        ax.text(1.42, o["budget"] + top * 0.015, f"Budget ₹{o['budget']:,}", ha="right", va="bottom",
                fontsize=8, color=INK_2)
        for b, v, ink in zip(bars, vals, (INK, "white")):
            ax.text(b.get_x() + b.get_width() / 2, v * 0.5, f"₹{v:,.0f}", ha="center", va="center",
                    fontsize=8.5, color=ink, fontweight="bold")
        cut = (1 - o["after"] / o["before"]) * 100
        status = "within" if o["budget_met"] else "over"
        ax.set_title(f"{title.replace(chr(10), ' ')}\n−{cut:.0f}% cost · {status} budget", loc="left", fontsize=9)
        ax.set_xticks([0, 1], ["Before", "After"])
        ax.set_xlim(-0.55, 1.5)
        ax.grid(axis="x", visible=False)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"₹{v:,.0f}"))
        ax.tick_params(axis="y", labelsize=8)
    handles = [plt.Rectangle((0, 0), 1, 1, color=GRAY_LIGHT), plt.Rectangle((0, 0), 1, 1, color=BLUE),
               plt.Line2D([0], [0], color=ORANGE, linewidth=2.2)]
    fig.legend(handles, ["Projected cost before optimization", "After optimization", "Budget"],
               loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.04))
    fig.suptitle("Budget vs projected 30-day cost (TNEB slabs), before and after the budget optimizer",
                 x=0.01, ha="left", fontsize=11.5, fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT / "fig_5_8_budget_vs_cost.png")
    plt.close(fig)

    return {"reference_temp_c": REFERENCE_TEMP_C, "appliances": appliance_table, "total_kwh_month": round(total, 1),
            "scenarios": out}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"forecasting": forecasting_figures(), "appliances": appliance_figures()}
    (OUT / "figure_metrics.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
