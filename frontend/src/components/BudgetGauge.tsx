interface Props {
  projectedCost: number;
  budget: number;
  originalCost: number;
}

export function BudgetGauge({ projectedCost, budget, originalCost }: Props) {
  const pct = Math.min((projectedCost / budget) * 100, 100);
  const overBudget = projectedCost > budget;
  const originalPct = Math.min((originalCost / budget) * 100, 999);

  return (
    <div className="gauge">
      <div className="gauge-header">
        <span className="gauge-label">Projected spend</span>
        <span className={`gauge-value ${overBudget ? "over" : "under"}`}>
          ₹{projectedCost.toFixed(2)}{" "}
          <span className="gauge-of">of ₹{budget.toFixed(2)}</span>
        </span>
      </div>
      <div className="gauge-track">
        <div
          className={`gauge-fill ${overBudget ? "over" : "under"}`}
          style={{ width: `${pct}%` }}
        />
        {originalPct > pct + 2 && originalPct <= 100 && (
          <div className="gauge-marker" style={{ left: `${originalPct}%` }} title="Original estimate" />
        )}
      </div>
      <div className="gauge-footer">
        {overBudget
          ? "Over budget even after optimization"
          : `${(100 - pct).toFixed(0)}% of budget remaining`}
      </div>
    </div>
  );
}
