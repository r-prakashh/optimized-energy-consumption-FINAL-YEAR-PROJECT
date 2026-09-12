const METRICS = [
  { label: "MAE", value: "2.56 kWh/day" },
  { label: "RMSE", value: "3.77 kWh/day" },
  { label: "WMAPE", value: "23.3%" },
  { label: "MAPE", value: "63.2% (unreliable here — see note)" },
];

const WEATHER_ABLATION = [
  { label: "MAE", baseline: "2.556", weather: "2.622", delta: "+2.6%" },
  { label: "RMSE", baseline: "3.773", weather: "3.801", delta: "+0.8%" },
  { label: "WMAPE", baseline: "23.34%", weather: "23.94%", delta: "+2.6%" },
];

export function Methodology() {
  return (
    <div className="methodology-page">
      <section className="section section-narrow">
        <span className="eyebrow">Methodology</span>
        <h1>
          How the forecast <em>actually works</em>
        </h1>
        <p className="lede">
          A transparent walkthrough of the data, modeling choices, and
          evaluation behind WattWise — written for anyone reviewing this as an
          academic project, not just using it as an app.
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Scope: built for Tamil Nadu, trained on UK data</h2>
        <p>
          This system targets Tamil Nadu households — the appliance catalog,
          tariff, and cooling-load heuristics below all reflect that. But the
          only public, appliance-level household dataset available for
          training is <strong>REFIT</strong>, recorded in 20 homes in
          Loughborough, England. That's a real gap, not a footnote: UK homes
          are heating-dominated (gas boilers, immersion heaters, almost no
          air conditioning) while Tamil Nadu homes are cooling-dominated (AC
          and fans, no heating, monsoon seasonality). The sections below
          explain exactly where that gap matters and how each part of the
          system deliberately handles it — sometimes by using the UK data
          anyway (where behaviour transfers, like weekday/weekend rhythm),
          and sometimes by explicitly avoiding it (where it doesn't, like
          heating-driven seasonality).
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Dataset</h2>
        <p>
          The forecasting model is trained on the{" "}
          <strong>REFIT Electrical Load Measurements</strong> dataset — two
          years of real household electricity data across 20 UK homes, logged
          at whole-house (<code>Aggregate</code>) and individual appliance
          channel level. The shipped model uses houses 1–5 (2,704 house-days).
        </p>
        <p>
          Energy is computed by time-weighted integration over the raw,
          irregularly-timestamped power readings — not a fixed sample-interval
          assumption — with logger gaps beyond 60 seconds excluded so outages
          aren't counted as continuous usage.
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Two-part consumption model</h2>
        <p>
          <strong>1. Household forecaster</strong> — a LightGBM regressor
          learns business-as-usual daily consumption from time features
          (day-of-week, weekend, month) and lag/rolling-window features (1-day,
          7-day, 30-day) — the baseline "if nothing changes" forecast. These
          features capture weekly rhythm and autocorrelation, which transfer
          across climates reasonably well; nothing here assumes UK-specific
          heating behaviour.
        </p>
        <p>
          <strong>2. Appliance-level estimator</strong> — converts your
          selected appliances and usage hours into daily kWh. REFIT's official
          per-house appliance-channel legend wasn't available in this dataset
          drop; an automatic signature-based classifier was tried and rejected
          after producing implausible results (multi-kW spikes even on
          otherwise low-power channels, consistent with sensor noise), so this
          component deliberately runs on nameplate-wattage arithmetic instead
          — a documented scope decision, not a gap.
        </p>
        <p>
          <strong>Air conditioner load gets one further adjustment</strong>{" "}
          not learned from REFIT at all (REFIT homes barely use AC): a live
          Tamil Nadu temperature reading (Open-Meteo, refreshed every 30 min)
          scales the AC energy estimate by how far the current temperature
          sits above a 24°C comfort baseline (±4% per °C, capped at 0.6×–1.6×)
          — a transparent physics heuristic, not a REFIT-learned relationship,
          kept deliberately separate for exactly that reason.
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Did adding weather help the forecaster? (an honest ablation)</h2>
        <p>
          Since REFIT houses are real UK homes, UK weather is at least a
          legitimate feature to test — unlike Tamil Nadu weather, which has no
          learned relationship in this data. Loughborough historical
          temperature and a heating-degree-day feature were added and
          re-evaluated on the same held-out split:
        </p>
        <div className="metrics-table">
          <div className="metrics-row">
            <span>Metric</span>
            <span>Baseline → +Weather</span>
          </div>
          {WEATHER_ABLATION.map((m) => (
            <div className="metrics-row" key={m.label}>
              <span>{m.label}</span>
              <span>
                {m.baseline} → {m.weather} ({m.delta})
              </span>
            </div>
          ))}
        </div>
        <p className="fine-print">
          Weather made it slightly worse, not better — the lag/rolling/
          day-of-year features already appear to capture most of the seasonal
          variation weather would explain, so the extra features mostly added
          noise on a 2,161-row training set. The deployed model excludes
          weather for two independent reasons now: this empirical result, and
          the fact that inference serves Tamil Nadu users where UK weather
          sensitivity wouldn't transfer anyway.
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Evaluation</h2>
        <p>
          Held out chronologically <em>within each house</em> (not just the
          tail of one house) to keep every house represented in both train and
          test splits:
        </p>
        <div className="metrics-table">
          {METRICS.map((m) => (
            <div className="metrics-row" key={m.label}>
              <span>{m.label}</span>
              <span>{m.value}</span>
            </div>
          ))}
        </div>
        <p className="fine-print">
          MAPE is unstable here because several held-out days have near-zero
          true consumption, which blows up any percentage metric with a
          near-zero denominator — WMAPE is the metric to trust for this
          dataset. For context, single-household day-ahead forecasting
          typically runs 20–40% WMAPE in published literature — individual
          homes are noisy in a way grid-level forecasts (which average
          thousands of households) aren't.
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Tariff</h2>
        <p>
          Cost is computed against TNEB's domestic LT-IA slab tariff
          (TNERC Tariff Order No. 6 of 2025, effective 1 Jul 2025;
          monthly-equivalent slabs, prorated to the requested plan duration):
          0–100 units free, ₹4.70/unit for 101–200, ₹6.30/unit for 201–300,
          ₹8.40/unit for 301–400, ₹11.55/unit above 400. Real tariffs are
          revised periodically plus a quarterly fuel-cost adjustment — verify
          against the current TNERC order before relying on this for an
          actual bill.
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Budget optimization</h2>
        <p>
          Deliberately rule-based rather than reinforcement-learning: each
          appliance carries a flexibility class (none/low/medium/high) and a
          minimum-hours floor. When the projected cost exceeds budget, the
          optimizer repeatedly trims hours from the highest{" "}
          <code>flexibility × hours × wattage</code> appliance first, in small
          steps, until either the budget is met or every appliance has hit its
          floor — so every recommendation traces back to a specific,
          explainable reason.
        </p>
        <p>
          <strong>Time-of-day shift opportunity</strong> — a separate,
          clearly-labeled illustrative analysis: TNEB doesn't bill
          time-of-day pricing today, but several Indian discoms are piloting
          it. For unattended, shiftable loads (washing machine, water heater,
          motor pump), the planner estimates what moving them to off-peak
          hours would save under a simulated peak/off-peak price signal —
          kept entirely separate from the real TNEB-slab cost calculation so
          the two are never conflated.
        </p>
      </section>

      <section className="section section-narrow">
        <h2>Scope &amp; limitations</h2>
        <p>
          This is a software forecasting and planning platform — not a
          smart-meter hardware project, and not an exact billing system.
          Outputs are approximate estimates intended for proactive household
          planning, not meter-accurate reconciliation.
        </p>
        <p>
          The clearest path to a fully India-calibrated system: retrain the
          household forecaster on an Indian/Tamil Nadu smart-meter dataset
          once one is available, which would let cooling-driven seasonality
          (rather than UK heating patterns) enter the model directly instead
          of being handled only at the appliance-adjustment layer.
        </p>
      </section>
    </div>
  );
}
