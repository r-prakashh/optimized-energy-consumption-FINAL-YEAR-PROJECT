import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  fetchApplianceCatalog,
  runScenario,
  type ApplianceCatalogEntry,
  type ApplianceChangeInput,
  type ApplianceSpecs,
  type ScenarioResponse,
} from "../api/client";
import { ApplianceIcon } from "../components/ApplianceIcons";
import { monthLabel } from "../utils/format";
import { useInsights } from "../context/InsightsContext";

interface ChangeRow extends ApplianceChangeInput {
  id: number;
}

const DEFAULT_HOURS: Record<string, number> = {
  air_conditioner: 8, fan: 10, television: 4, lighting: 6, refrigerator: 24,
  washing_machine: 1, computer: 6, microwave: 0.3, water_heater: 0.5, motor_pump: 0.5,
};

let nextId = 1;

function defaultSpecs(a?: ApplianceCatalogEntry): ApplianceSpecs {
  const s: ApplianceSpecs = {};
  a?.specs.forEach((f) => (s[f.key] = f.default));
  return s;
}

function prettyOption(v: string | number | boolean) {
  return typeof v === "string" ? v.replace(/_/g, " ") : String(v);
}

export function Simulator() {
  const { analysis } = useInsights();
  const [catalog, setCatalog] = useState<ApplianceCatalogEntry[]>([]);
  const [rows, setRows] = useState<ChangeRow[]>([]);
  const [manualBaseline, setManualBaseline] = useState(250);
  const [useBills, setUseBills] = useState(!!analysis);
  const [result, setResult] = useState<ScenarioResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchApplianceCatalog()
      .then((data) => {
        setCatalog(data);
        const ac = data.find((a) => a.category === "air_conditioner");
        setRows([{ id: nextId++, action: "add", category: "air_conditioner", quantity: 1, hours_per_day: 8, specs: defaultSpecs(ac) }]);
      })
      .catch(() => setError("Could not reach the backend API. Is it running at http://localhost:8000?"));
  }, []);

  function update(id: number, patch: Partial<ChangeRow>) {
    setRows((prev) =>
      prev.map((r) => {
        if (r.id !== id) return r;
        const merged = { ...r, ...patch };
        if (patch.category && patch.category !== r.category) {
          merged.specs = defaultSpecs(catalog.find((a) => a.category === patch.category));
          merged.hours_per_day = DEFAULT_HOURS[patch.category] ?? 4;
        }
        return merged;
      })
    );
  }

  function addRow(action: "add" | "remove") {
    const cat = action === "add" ? "fan" : "water_heater";
    setRows((p) => [
      ...p,
      { id: nextId++, action, category: cat, quantity: 1, hours_per_day: DEFAULT_HOURS[cat], specs: defaultSpecs(catalog.find((a) => a.category === cat)) },
    ]);
  }

  async function simulate() {
    if (!rows.length) return;
    setError(null);
    setLoading(true);
    try {
      const res = await runScenario({
        changes: rows.map(({ action, category, quantity, hours_per_day, specs }) => ({ action, category, quantity, hours_per_day, specs })),
        ...(useBills && analysis
          ? { baseline_months: analysis.forecast.map((f) => [f.label, f.kwh] as [string, number]) }
          : { baseline_monthly_kwh: manualBaseline }),
      });
      setResult(res);
    } catch {
      setError("Simulation failed — check the inputs.");
    } finally {
      setLoading(false);
    }
  }

  const up = result && result.delta_monthly_cost > 0;

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="eyebrow">Appliance what-if</span>
        <h1>Buying or retiring an appliance? See the bill first.</h1>
        <p className="subtitle">
          Add appliances you're planning to buy, or remove ones you're getting rid of, and WattWise
          predicts the new monthly units and TNEB bill — including slab jumps a flat-rate calculator misses.
        </p>
      </header>

      {error && <div className="banner error">{error}</div>}

      <section className="panel">
        <h2>Starting point</h2>
        <div className="baseline-options">
          <label className={`baseline-option ${useBills && analysis ? "active" : ""} ${!analysis ? "disabled" : ""}`}>
            <input type="radio" checked={useBills && !!analysis} disabled={!analysis} onChange={() => setUseBills(true)} />
            <div>
              <strong>My bill forecast</strong>
              {analysis ? (
                <span>
                  {analysis.forecast.map((f) => `${monthLabel(f.label)}: ${f.kwh.toFixed(0)} kWh`).join(" · ")}
                </span>
              ) : (
                <span>
                  <Link to="/bills">Upload your bills</Link> to simulate on top of your own forecast.
                </span>
              )}
            </div>
          </label>
          <label className={`baseline-option ${!useBills || !analysis ? "active" : ""}`}>
            <input type="radio" checked={!useBills || !analysis} onChange={() => setUseBills(false)} />
            <div>
              <strong>Typical month</strong>
              <span className="baseline-input">
                <input type="number" min={0} value={manualBaseline} onChange={(e) => setManualBaseline(Number(e.target.value))} onClick={() => setUseBills(false)} />
                kWh / month
              </span>
            </div>
          </label>
        </div>

        <h2>Changes</h2>
        <div className="change-list">
          {rows.map((r) => {
            const entry = catalog.find((a) => a.category === r.category);
            return (
              <div className={`change-row ${r.action}`} key={r.id}>
                <div className="change-toggle">
                  <button className={r.action === "add" ? "on add" : ""} onClick={() => update(r.id, { action: "add" })}>+ Add</button>
                  <button className={r.action === "remove" ? "on remove" : ""} onClick={() => update(r.id, { action: "remove" })}>− Remove</button>
                </div>
                <div className="change-appliance">
                  <ApplianceIcon category={r.category} />
                  <select value={r.category} onChange={(e) => update(r.id, { category: e.target.value })}>
                    {catalog.map((a) => (
                      <option key={a.category} value={a.category}>{a.label}</option>
                    ))}
                  </select>
                </div>
                <label className="change-field">
                  Qty
                  <input type="number" min={1} max={20} value={r.quantity} onChange={(e) => update(r.id, { quantity: Math.max(1, Number(e.target.value)) })} />
                </label>
                <label className="change-field">
                  Hours/day
                  <input type="number" min={0} max={24} step={0.5} value={r.hours_per_day} onChange={(e) => update(r.id, { hours_per_day: Number(e.target.value) })} />
                </label>
                {entry?.specs.map((f) => (
                  <label className="change-field" key={f.key}>
                    {f.label}
                    {f.type === "boolean" ? (
                      <select value={String(r.specs[f.key])} onChange={(e) => update(r.id, { specs: { ...r.specs, [f.key]: e.target.value === "true" } })}>
                        <option value="true">Yes</option>
                        <option value="false">No</option>
                      </select>
                    ) : (
                      <select
                        value={String(r.specs[f.key])}
                        onChange={(e) => {
                          const opt = f.options.find((o) => String(o) === e.target.value);
                          update(r.id, { specs: { ...r.specs, [f.key]: opt ?? e.target.value } });
                        }}
                      >
                        {f.options.map((o) => (
                          <option key={String(o)} value={String(o)}>{prettyOption(o)} {f.unit}</option>
                        ))}
                      </select>
                    )}
                  </label>
                ))}
                <button className="remove-btn" onClick={() => setRows((p) => p.filter((x) => x.id !== r.id))} aria-label="Delete change">×</button>
              </div>
            );
          })}
        </div>
        <div className="readings-actions" style={{ marginTop: 14 }}>
          <button className="secondary small" onClick={() => addRow("add")}>+ Add an appliance</button>
          <button className="secondary small" onClick={() => addRow("remove")}>− Remove an appliance</button>
        </div>

        <div className="actions">
          <button className="primary" disabled={loading || !rows.length || !catalog.length} onClick={simulate}>
            {loading ? "Predicting…" : "Predict my new bill"}
          </button>
        </div>
      </section>

      {result && (
        <section className="results-grid">
          <div className="panel span-2">
            <h2>Prediction</h2>
            <div className={`verdict ${up ? "up" : "down"}`}>{result.verdict}</div>
            <div className="stat-row four">
              <div className="stat-card">
                <span className="stat-label">Now</span>
                <span className="stat-value">{result.baseline_monthly_kwh.toFixed(0)} kWh</span>
                <span className="stat-sub">≈ ₹{result.baseline_monthly_cost.toFixed(0)} / month</span>
              </div>
              <div className={`stat-card ${up ? "warn" : "ok"}`}>
                <span className="stat-label">After changes</span>
                <span className="stat-value">{result.new_monthly_kwh.toFixed(0)} kWh</span>
                <span className="stat-sub">≈ ₹{result.new_monthly_cost.toFixed(0)} / month</span>
              </div>
              <div className={`stat-card ${up ? "warn" : "ok"}`}>
                <span className="stat-label">Change</span>
                <span className="stat-value">{result.delta_monthly_cost > 0 ? "+" : "−"}₹{Math.abs(result.delta_monthly_cost).toFixed(0)}</span>
                <span className="stat-sub">{result.delta_monthly_kwh > 0 ? "+" : ""}{result.delta_monthly_kwh.toFixed(0)} kWh / month</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Per year</span>
                <span className="stat-value">{result.delta_monthly_cost > 0 ? "+" : "−"}₹{Math.abs(result.delta_monthly_cost * 12).toFixed(0)}</span>
                <span className="stat-sub">at today's tariff</span>
              </div>
            </div>
          </div>

          <div className="panel">
            <h2>{result.months.length ? "Forecast bills, before vs after" : "Monthly bill, before vs after"}</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={
                  result.months.length
                    ? result.months.map((m) => ({ name: monthLabel(m.label), Before: m.baseline_cost, After: m.new_cost }))
                    : [{ name: "Typical month", Before: result.baseline_monthly_cost, After: result.new_monthly_cost }]
                }
                margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
                <YAxis tick={{ fontSize: 11, fill: "var(--text-secondary)" }} unit="₹" width={64} />
                <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} formatter={(v) => `₹${Number(v).toFixed(0)}`} contentStyle={{ fontSize: 12, background: "#17181c", border: "1px solid #2a2b31", borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="Before" fill="#5b5d66" radius={[6, 6, 0, 0]} maxBarSize={40} />
                <Bar dataKey="After" fill={up ? "#e50914" : "#2ecc71"} radius={[6, 6, 0, 0]} maxBarSize={40} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="panel">
            <h2>Per-appliance impact</h2>
            <div className="impact-list">
              {result.changes.map((c, i) => (
                <div className="impact-row" key={i}>
                  <ApplianceIcon category={c.category} />
                  <div>
                    <strong>{c.action === "add" ? "Add" : "Remove"} {c.quantity}× {c.label}</strong>
                    <span>{c.hours_per_day} h/day</span>
                  </div>
                  <span className={c.monthly_kwh > 0 ? "delta up" : "delta down"}>
                    {c.monthly_kwh > 0 ? "+" : ""}{c.monthly_kwh.toFixed(0)} kWh/mo
                  </span>
                </div>
              ))}
            </div>
            {result.tips.length > 0 && (
              <>
                <h2>Tips</h2>
                <ul className="tip-list">
                  {result.tips.map((t) => <li key={t}>{t}</li>)}
                </ul>
              </>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
