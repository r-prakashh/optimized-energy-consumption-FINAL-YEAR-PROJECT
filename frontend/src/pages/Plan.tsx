import { useEffect, useState } from "react";
import {
  createPlan,
  fetchApplianceCatalog,
  whatIf,
  type ApplianceCatalogEntry,
  type ApplianceSpecs,
  type PlanResponse,
} from "../api/client";
import { ActionPlan } from "../components/ActionPlan";
import { ApplianceCompareBars } from "../components/ApplianceCompareBars";
import { ApplianceSelector, type SelectedAppliance } from "../components/ApplianceSelector";
import { ApplianceShareChart } from "../components/ApplianceShareChart";
import { BudgetGauge } from "../components/BudgetGauge";
import { ForecastChart } from "../components/ForecastChart";
import { TodShiftCard } from "../components/TodShiftCard";

const STEPS = ["Budget", "Appliances", "Your plan"];

function defaultSpecs(appliance: ApplianceCatalogEntry): ApplianceSpecs {
  const specs: ApplianceSpecs = {};
  for (const field of appliance.specs) {
    specs[field.key] = field.default;
  }
  return specs;
}

export function Plan() {
  const [step, setStep] = useState(0);
  const [catalog, setCatalog] = useState<ApplianceCatalogEntry[]>([]);
  const [selected, setSelected] = useState<Record<string, SelectedAppliance>>({});
  const [budget, setBudget] = useState(3000);
  const [durationDays, setDurationDays] = useState(30);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);

  useEffect(() => {
    fetchApplianceCatalog()
      .then((data) => {
        setCatalog(data);
        const defaults = ["air_conditioner", "fan", "television", "lighting"];
        const initial: Record<string, SelectedAppliance> = {};
        data.forEach((a) => {
          if (defaults.includes(a.category)) {
            initial[a.category] = { hours: Math.min(4, a.max_hours), specs: defaultSpecs(a) };
          }
        });
        setSelected(initial);
      })
      .catch(() =>
        setCatalogError(
          "Could not reach the backend API. Is it running at http://localhost:8000?"
        )
      );
  }, []);

  function handleToggle(category: string, checked: boolean) {
    setSelected((prev) => {
      const next = { ...prev };
      if (!checked) {
        delete next[category];
        return next;
      }
      const appliance = catalog.find((a) => a.category === category);
      if (!appliance) return prev;
      next[category] = { hours: Math.min(4, appliance.max_hours), specs: defaultSpecs(appliance) };
      return next;
    });
  }

  function handleHoursChange(category: string, hours: number) {
    setSelected((prev) => ({ ...prev, [category]: { ...prev[category], hours } }));
  }

  function handleSpecChange(category: string, key: string, value: string | number | boolean) {
    setSelected((prev) => ({
      ...prev,
      [category]: { ...prev[category], specs: { ...prev[category].specs, [key]: value } },
    }));
  }

  async function runPlan(useWhatIf: boolean) {
    if (Object.keys(selected).length === 0) {
      setError("Select at least one appliance.");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const payload = {
        budget,
        duration_days: durationDays,
        appliances: Object.entries(selected).map(([category, { hours, specs }]) => ({
          category,
          hours_per_day: hours,
          specs,
        })),
      };
      const result = useWhatIf ? await whatIf(payload) : await createPlan(payload);
      setPlan(result);
      setStep(2);
    } catch {
      setError("Something went wrong generating the plan. Check the backend logs.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="eyebrow">The planner</span>
        <h1>Build your personalized energy plan</h1>
        <p className="subtitle">
          Predict consumption, estimate electricity cost, and get a
          budget-constrained appliance usage plan.
        </p>
      </header>

      {catalogError && <div className="banner error">{catalogError}</div>}

      <div className="stepper">
        {STEPS.map((label, i) => (
          <button
            key={label}
            className={`step-pill ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}
            onClick={() => (i <= step || plan) && i !== 2 && setStep(i)}
            disabled={i === 2 && !plan}
          >
            <span className="step-pill-n">{i + 1}</span>
            {label}
          </button>
        ))}
      </div>

      {step === 0 && (
        <section className="panel wizard-panel">
          <h2>Your budget &amp; duration</h2>
          <div className="field-row">
            <label>
              Budget (₹)
              <input
                type="number"
                min={1}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
              />
            </label>
            <label>
              Duration (days)
              <input
                type="number"
                min={1}
                max={90}
                value={durationDays}
                onChange={(e) => setDurationDays(Number(e.target.value))}
              />
            </label>
          </div>
          <div className="actions">
            <button className="primary" onClick={() => setStep(1)}>
              Next: Select appliances
            </button>
          </div>
        </section>
      )}

      {step === 1 && (
        <section className="panel wizard-panel wizard-panel-wide">
          <h2>Select your appliances</h2>
          <p className="hint">
            Add the appliance model details you know (tonnage, star rating,
            capacity) for a more accurate estimate — or skip them and we'll
            use typical values.
          </p>
          <ApplianceSelector
            catalog={catalog}
            selected={selected}
            onToggle={handleToggle}
            onHoursChange={handleHoursChange}
            onSpecChange={handleSpecChange}
          />
          {error && <div className="banner error">{error}</div>}
          <div className="actions">
            <button className="secondary" onClick={() => setStep(0)}>
              Back
            </button>
            <button className="primary" disabled={loading} onClick={() => runPlan(false)}>
              {loading ? "Calculating..." : "Generate Plan"}
            </button>
          </div>
        </section>
      )}

      {step === 2 && plan && (
        <section className="results-grid">
          <div className="panel">
            <h2>Budget outcome</h2>
            <BudgetGauge
              projectedCost={plan.projected_cost}
              budget={plan.budget}
              originalCost={plan.original_cost}
            />
            <div className="stat-row" style={{ marginTop: 20 }}>
              <div className="stat-card">
                <span className="stat-label">Total energy</span>
                <span className="stat-value">{plan.projected_total_kwh.toFixed(1)} kWh</span>
                <span className="stat-sub">over {plan.duration_days} days</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Original estimate</span>
                <span className="stat-value">₹{plan.original_cost.toFixed(2)}</span>
                {plan.original_cost > plan.projected_cost && (
                  <span className="stat-sub savings">
                    Saved ₹{(plan.original_cost - plan.projected_cost).toFixed(2)}
                  </span>
                )}
              </div>
            </div>

            <h2 style={{ marginTop: 28 }}>Forecast (next {plan.duration_days} days)</h2>
            <ForecastChart forecastDailyKwh={plan.forecast_daily_kwh} />
          </div>

          <div className="panel">
            <h2>Energy share by appliance</h2>
            <ApplianceShareChart appliances={plan.appliances} />
          </div>

          <div className="panel span-2">
            <h2>Your action plan</h2>
            <ActionPlan lines={plan.action_plan} />
          </div>

          <div className="panel span-2">
            <h2>Recommended hours — before &amp; after</h2>
            <ApplianceCompareBars appliances={plan.appliances} />
          </div>

          {plan.tod_shift_opportunities.length > 0 && (
            <div className="panel span-2">
              <TodShiftCard
                opportunities={plan.tod_shift_opportunities}
                totalSaving={plan.tod_total_saving_for_period}
                durationDays={plan.duration_days}
              />
            </div>
          )}

          {!plan.budget_met && (
            <p className="banner warn span-2">
              Even at minimum hours for essential appliances, the projected
              cost exceeds your budget. Consider increasing the budget or
              removing a high-consumption appliance from the plan.
            </p>
          )}

          <div className="actions span-2">
            <button className="secondary" onClick={() => setStep(1)}>
              Edit appliances
            </button>
            <button className="primary" disabled={loading} onClick={() => runPlan(true)}>
              {loading ? "Recalculating..." : "Re-run What-If"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
