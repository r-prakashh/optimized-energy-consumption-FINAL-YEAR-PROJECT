const METRICS = [
  { label: "MAE", value: "2.56 kWh/day" },
  { label: "RMSE", value: "3.77 kWh/day" },
  { label: "WMAPE", value: "23.3%" },
  { label: "MAPE", value: "63.2% (unreliable here — see note)" },
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
          7-day, 30-day) — the baseline "if nothing changes" forecast.
        </p>
        <p>
          <strong>2. Appliance-level estimator</strong> — converts your
          selected appliances and usage hours into daily kWh. REFIT's official
          per-house appliance-channel legend wasn't available in this dataset
          drop; an automatic signature-based classifier was tried and rejected
          after producing implausible results (see the project README for the
          full writeup), so this component deliberately runs on nameplate-
          wattage arithmetic instead — a documented scope decision, not a gap.
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
          dataset.
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
      </section>

      <section className="section section-narrow">
        <h2>Scope</h2>
        <p>
          This is a software forecasting and planning platform — not a
          smart-meter hardware project, and not an exact billing system.
          Outputs are approximate estimates intended for proactive household
          planning.
        </p>
      </section>
    </div>
  );
}
