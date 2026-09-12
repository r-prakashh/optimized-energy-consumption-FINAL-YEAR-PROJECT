import { useEffect, useState } from "react";
import {
  createPlan,
  fetchApplianceCatalog,
  whatIf,
  type ApplianceCatalogEntry,
  type PlanResponse,
} from "../api/client";
import { ApplianceSelector } from "../components/ApplianceSelector";
import { ForecastChart } from "../components/ForecastChart";
import { PlanResults } from "../components/PlanResults";

export function Plan() {
  const [catalog, setCatalog] = useState<ApplianceCatalogEntry[]>([]);
  const [selected, setSelected] = useState<Record<string, number>>({});
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
        const initial: Record<string, number> = {};
        data.forEach((a) => {
          if (defaults.includes(a.category)) {
            initial[a.category] = Math.min(4, a.max_hours);
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

  function handleApplianceChange(category: string, hours: number | null) {
    setSelected((prev) => {
      const next = { ...prev };
      if (hours === null) {
        delete next[category];
      } else {
        next[category] = hours;
      }
      return next;
    });
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
        appliances: Object.entries(selected).map(([category, hours_per_day]) => ({
          category,
          hours_per_day,
        })),
      };
      const result = useWhatIf ? await whatIf(payload) : await createPlan(payload);
      setPlan(result);
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

      <main className="app-grid">
        <section className="panel">
          <h2>1. Your budget &amp; duration</h2>
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

          <h2>2. Select appliances</h2>
          <ApplianceSelector
            catalog={catalog}
            selected={selected}
            onChange={handleApplianceChange}
          />

          {error && <div className="banner error">{error}</div>}

          <div className="actions">
            <button
              className="primary"
              disabled={loading}
              onClick={() => runPlan(false)}
            >
              {loading ? "Calculating..." : "Generate Plan"}
            </button>
            {plan && (
              <button
                className="secondary"
                disabled={loading}
                onClick={() => runPlan(true)}
              >
                Re-run What-If
              </button>
            )}
          </div>
        </section>

        <section className="panel">
          <h2>3. Forecast &amp; recommendations</h2>
          {!plan && (
            <p className="empty-state">
              Fill in your budget and appliances, then generate a plan to see
              your forecast and cost-optimized appliance schedule here.
            </p>
          )}
          {plan && (
            <>
              <ForecastChart forecastDailyKwh={plan.forecast_daily_kwh} />
              <PlanResults plan={plan} />
            </>
          )}
        </section>
      </main>
    </div>
  );
}
