import type { PlanResponse } from "../api/client";

interface Props {
  plan: PlanResponse;
}

export function PlanResults({ plan }: Props) {
  const savings = plan.original_cost - plan.projected_cost;

  return (
    <div className="plan-results">
      <div className="stat-row">
        <div className={`stat-card ${plan.budget_met ? "ok" : "warn"}`}>
          <span className="stat-label">
            {plan.budget_met ? "Within budget" : "Still over budget"}
          </span>
          <span className="stat-value">₹{plan.projected_cost.toFixed(2)}</span>
          <span className="stat-sub">of ₹{plan.budget.toFixed(2)} budget</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Original estimate</span>
          <span className="stat-value">₹{plan.original_cost.toFixed(2)}</span>
          {savings > 0 && (
            <span className="stat-sub savings">
              Saved ₹{savings.toFixed(2)}
            </span>
          )}
        </div>
        <div className="stat-card">
          <span className="stat-label">Total energy</span>
          <span className="stat-value">{plan.projected_total_kwh.toFixed(1)} kWh</span>
          <span className="stat-sub">over {plan.duration_days} days</span>
        </div>
      </div>

      <h3>Recommended daily appliance hours</h3>
      <table className="plan-table">
        <thead>
          <tr>
            <th>Appliance</th>
            <th>Original</th>
            <th>Recommended</th>
            <th>Daily kWh</th>
          </tr>
        </thead>
        <tbody>
          {plan.appliances.map((a) => (
            <tr key={a.category} className={a.reduced ? "reduced" : ""}>
              <td>{a.label}</td>
              <td>{a.original_hours} hrs</td>
              <td>
                {a.recommended_hours} hrs
                {a.reduced && <span className="reduced-badge">reduced</span>}
              </td>
              <td>{a.daily_kwh.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {!plan.budget_met && (
        <p className="banner warn">
          Even at minimum hours for essential appliances, the projected cost
          exceeds your budget. Consider increasing the budget or removing a
          high-consumption appliance from the plan.
        </p>
      )}
    </div>
  );
}
