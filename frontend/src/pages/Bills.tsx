import { useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";
import {
  analyzeBills,
  uploadBills,
  type BillReadingInput,
  type BillUploadResult,
} from "../api/client";
import { BillTrendChart } from "../components/BillTrendChart";
import { monthLabel } from "../utils/format";
import { useInsights } from "../context/InsightsContext";

interface Row extends BillReadingInput {
  id: number;
  source: string;
  confidence: number | null;
  notes: string[];
}

const MODEL_NAMES: Record<string, string> = {
  naive: "Naive (last value)",
  seasonal_naive: "Seasonal naive (TN index)",
  holt: "Damped Holt smoothing",
  ridge: "Ridge regression (trend + season)",
};

let nextId = 1;

function sampleRows(): Row[] {
  // A year of TNEB bi-monthly bills for a 2-AC Chennai flat.
  const data: [string, number, number][] = [
    ["2025-11-14", 410, 1508], ["2026-01-13", 352, 1146], ["2026-03-14", 398, 1418],
    ["2026-05-13", 612, 3001], ["2026-07-14", 548, 2486], ["2026-09-12", 470, 1883],
  ];
  return data.map(([d, u, a]) => ({
    id: nextId++, period_end: d, period_days: 60, units_kwh: u, amount_inr: a,
    source: "sample", confidence: null, notes: [],
  }));
}

function blankRow(): Row {
  return {
    id: nextId++, period_end: new Date().toISOString().slice(0, 10), period_days: 60,
    units_kwh: 0, amount_inr: null, source: "manual", confidence: null, notes: [],
  };
}

const SOURCE_LABEL: Record<string, string> = {
  pdf_text_layer: "PDF text",
  ocr: "OCR",
  ai_vision: "AI vision",
  manual: "Manual",
  sample: "Sample",
};

export function Bills() {
  const { readings, setReadings, analysis, setAnalysis } = useInsights();
  const [rows, setRows] = useState<Row[]>(() =>
    readings.map((r) => ({ ...r, id: nextId++, source: "manual", confidence: null, notes: [] }))
  );
  const [uploading, setUploading] = useState(false);
  const [fileResults, setFileResults] = useState<BillUploadResult[]>([]);
  const [analyzing, setAnalyzing] = useState(false);
  const [horizon, setHorizon] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFiles(list: FileList | File[]) {
    const files = Array.from(list);
    if (!files.length) return;
    setError(null);
    setUploading(true);
    try {
      const res = await uploadBills(files);
      setFileResults(res.files);
      const added: Row[] = [];
      res.files.forEach((f) =>
        f.readings.forEach((r) =>
          added.push({
            id: nextId++,
            period_end: r.period_end ?? "",
            period_days: r.period_days,
            units_kwh: r.units_kwh ?? 0,
            amount_inr: r.amount_inr,
            source: r.source,
            confidence: r.confidence,
            notes: r.notes,
          })
        )
      );
      setRows((prev) => [...prev, ...added]);
    } catch {
      setError("Upload failed — is the backend running?");
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  }

  function update(id: number, patch: Partial<Row>) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  const validRows = rows.filter((r) => r.period_end && r.units_kwh > 0);

  async function analyse() {
    if (!validRows.length) {
      setError("Add at least one bill with a date and units.");
      return;
    }
    setError(null);
    setAnalyzing(true);
    try {
      const payload = validRows.map(({ period_end, period_days, units_kwh, amount_inr }) => ({
        period_end, period_days, units_kwh, amount_inr: amount_inr || null,
      }));
      const res = await analyzeBills(payload, horizon);
      setReadings(payload);
      setAnalysis(res);
      setTimeout(() => document.getElementById("bill-results")?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Analysis failed — check the readings.");
    } finally {
      setAnalyzing(false);
    }
  }

  const next = analysis?.forecast[0];
  const bestScore = analysis ? Math.min(...Object.values(analysis.model_scores)) : 0;

  return (
    <div className="app-shell">
      <header className="app-header">
        <span className="eyebrow">Bill insights</span>
        <h1>Upload your past bills, see where you're heading</h1>
        <p className="subtitle">
          Drop in old electricity bills — PDF e-bills, phone photos, scans or a handwritten list of
          readings. WattWise reads them, learns your trend, flags unusual months and forecasts what's
          coming, with advice for using less.
        </p>
      </header>

      <section className="panel">
        <h2>1 · Add your bills</h2>
        <div
          className={`dropzone ${dragOver ? "over" : ""} ${uploading ? "busy" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          onClick={() => !uploading && inputRef.current?.click()}
          role="button"
          tabIndex={0}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,image/*"
            multiple
            hidden
            onChange={(e) => e.target.files && handleFiles(e.target.files)}
          />
          <div className="dropzone-icon" aria-hidden="true">
            <svg viewBox="0 0 48 48" width="44" height="44" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <path d="M28 6H14a4 4 0 0 0-4 4v28a4 4 0 0 0 4 4h20a4 4 0 0 0 4-4V16z" />
              <path d="M28 6v10h10" />
              <path d="M24 34V22m-6 6 6-6 6 6" />
            </svg>
          </div>
          {uploading ? (
            <strong>Reading your bills… (OCR takes a few seconds per page)</strong>
          ) : (
            <>
              <strong>Drag &amp; drop bills here, or click to browse</strong>
              <span>PDF, JPG, PNG, WEBP · up to 12 files · 10 MB each · nothing is stored</span>
            </>
          )}
        </div>

        {fileResults.length > 0 && (
          <ul className="file-results">
            {fileResults.map((f, i) => (
              <li key={i} className={f.error ? "bad" : "good"}>
                <span className="file-name">{f.filename}</span>
                {f.error ? (
                  <span>{f.error}</span>
                ) : (
                  <span>
                    {f.readings.length} reading{f.readings.length === 1 ? "" : "s"} via{" "}
                    {SOURCE_LABEL[f.method] ?? f.method}
                    {f.ocr_confidence != null && ` · OCR confidence ${(f.ocr_confidence * 100).toFixed(0)}%`}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}

        <div className="readings-head">
          <h3>Readings {rows.length > 0 && <span className="muted">({rows.length})</span>}</h3>
          <div className="readings-actions">
            <button className="secondary small" onClick={() => setRows((p) => [...p, blankRow()])}>
              + Add manually
            </button>
            <button className="secondary small" onClick={() => setRows(sampleRows())}>
              Try sample data
            </button>
            {rows.length > 0 && (
              <button className="secondary small" onClick={() => setRows([])}>
                Clear
              </button>
            )}
          </div>
        </div>
        <p className="hint">
          Check every value — OCR can misread a digit. TNEB bills cover ~60 days; monthly bills 30.
        </p>

        {rows.length === 0 ? (
          <p className="empty-state">No readings yet. Upload a bill, add one manually, or try the sample data.</p>
        ) : (
          <div className="table-scroll">
            <table className="readings-table">
              <thead>
                <tr>
                  <th>Bill / reading date</th>
                  <th>Period (days)</th>
                  <th>Units (kWh)</th>
                  <th>Amount (₹)</th>
                  <th>Source</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className={r.notes.length ? "has-notes" : ""}>
                    <td>
                      <input type="date" value={r.period_end} onChange={(e) => update(r.id, { period_end: e.target.value })} />
                    </td>
                    <td>
                      <input type="number" min={7} max={92} value={r.period_days} onChange={(e) => update(r.id, { period_days: Number(e.target.value) })} />
                    </td>
                    <td>
                      <input type="number" min={0} value={r.units_kwh || ""} placeholder="?" onChange={(e) => update(r.id, { units_kwh: Number(e.target.value) })} />
                    </td>
                    <td>
                      <input type="number" min={0} value={r.amount_inr ?? ""} placeholder="optional" onChange={(e) => update(r.id, { amount_inr: e.target.value ? Number(e.target.value) : null })} />
                    </td>
                    <td>
                      <span className={`source-badge src-${r.source}`} title={r.notes.join(" ")}>
                        {SOURCE_LABEL[r.source] ?? r.source}
                        {r.confidence != null && r.confidence < 0.7 && " · check"}
                      </span>
                    </td>
                    <td>
                      <button className="remove-btn" onClick={() => setRows((p) => p.filter((x) => x.id !== r.id))} aria-label="Remove row">
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {rows.some((r) => r.notes.length) && (
          <ul className="parse-notes">
            {rows.flatMap((r) => r.notes.map((n, i) => <li key={`${r.id}-${i}`}>{n}</li>))}
          </ul>
        )}

        {error && <div className="banner error">{error}</div>}
        <div className="actions">
          <label className="inline-select">
            Forecast
            <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
              <option value={3}>3 months</option>
              <option value={6}>6 months</option>
            </select>
          </label>
          <button className="primary" disabled={analyzing || !validRows.length} onClick={analyse}>
            {analyzing ? "Analysing…" : `Analyse ${validRows.length || ""} bill${validRows.length === 1 ? "" : "s"}`}
          </button>
        </div>
      </section>

      {analysis && (
        <section className="results-grid" id="bill-results">
          <div className="panel span-2">
            <h2>2 · Your consumption trend &amp; forecast</h2>
            <div className="stat-row four">
              <div className="stat-card">
                <span className="stat-label">Average</span>
                <span className="stat-value">{analysis.avg_monthly_kwh.toFixed(0)} kWh</span>
                <span className="stat-sub">per month · ≈ ₹{analysis.avg_monthly_cost.toFixed(0)}</span>
              </div>
              <div className={`stat-card ${analysis.trend_direction === "rising" ? "warn" : analysis.trend_direction === "falling" ? "ok" : ""}`}>
                <span className="stat-label">Trend</span>
                <span className="stat-value">
                  {analysis.trend_direction === "rising" ? "▲" : analysis.trend_direction === "falling" ? "▼" : "→"}{" "}
                  {analysis.trend_pct_per_month > 0 ? "+" : ""}
                  {analysis.trend_pct_per_month.toFixed(1)}%
                </span>
                <span className="stat-sub">per month, season-adjusted</span>
              </div>
              {next && (
                <div className="stat-card">
                  <span className="stat-label">Next month</span>
                  <span className="stat-value">{next.kwh.toFixed(0)} kWh</span>
                  <span className="stat-sub">≈ ₹{next.estimated_cost.toFixed(0)} · {monthLabel(next.label)}</span>
                </div>
              )}
              <div className="stat-card">
                <span className="stat-label">Always-on load</span>
                <span className="stat-value">{analysis.baseload_kwh_per_day.toFixed(1)} kWh</span>
                <span className="stat-sub">per day (fridge, standby…)</span>
              </div>
            </div>
            <div style={{ marginTop: 24 }}>
              <BillTrendChart analysis={analysis} />
            </div>
            <p className="fine-print">
              Orange bars are unusual months (robust z-score &gt; 2.5 after removing the Tamil Nadu
              seasonal pattern). The shaded band is the 80% forecast range.
            </p>
            {analysis.notes.map((n) => (
              <div className="banner warn" key={n}>{n}</div>
            ))}
          </div>

          <div className="panel">
            <h2>3 · Advice for you</h2>
            <div className="advice-list">
              {analysis.advice.map((a, i) => (
                <div className={`advice-card ${a.kind}`} key={i}>
                  <strong>{a.title}</strong>
                  <p>{a.body}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="panel">
            <h2>Optimal usage target</h2>
            <div className="target-card">
              <div className="target-numbers">
                <div>
                  <span className="stat-label">Expected</span>
                  <span className="target-big">{analysis.optimal_target.current_monthly_kwh.toFixed(0)}</span>
                  <span className="stat-sub">kWh / month</span>
                </div>
                <span className="target-arrow">→</span>
                <div>
                  <span className="stat-label">Target</span>
                  <span className="target-big ok">{analysis.optimal_target.target_monthly_kwh.toFixed(0)}</span>
                  <span className="stat-sub">{analysis.optimal_target.target_daily_kwh.toFixed(1)} kWh / day</span>
                </div>
              </div>
              <p>{analysis.optimal_target.reason}</p>
              {analysis.optimal_target.monthly_saving_inr > 0 && (
                <p className="savings-line">
                  Saves about <strong>₹{analysis.optimal_target.monthly_saving_inr.toFixed(0)}/month</strong>
                </p>
              )}
            </div>

            <h2>How the forecast was chosen</h2>
            <p className="hint" style={{ marginTop: 0 }}>
              Candidate models compete on a rolling backtest of <em>your</em> bills; the lowest error wins.
            </p>
            <div className="model-table">
              {Object.entries(analysis.model_scores)
                .sort((a, b) => a[1] - b[1])
                .map(([name, score]) => (
                  <div className={`model-row ${name === analysis.model_used ? "winner" : ""}`} key={name}>
                    <span>{MODEL_NAMES[name] ?? name}</span>
                    <span className="model-bar">
                      <span style={{ width: `${Math.min(100, (bestScore / Math.max(score, 0.01)) * 100)}%` }} />
                    </span>
                    <span>{score.toFixed(1)} kWh MAE</span>
                  </div>
                ))}
              {Object.keys(analysis.model_scores).length === 0 && (
                <p className="empty-state">Too few bills to backtest — using the seasonal prior ({MODEL_NAMES[analysis.model_used]}).</p>
              )}
            </div>
          </div>

          <div className="panel span-2 next-steps">
            <div>
              <h2>Planning to add or remove appliances?</h2>
              <p className="hint" style={{ marginTop: 0 }}>
                See how a new AC, geyser or BLDC fan changes these forecast bills month by month.
              </p>
            </div>
            <Link to="/simulator" className="btn-primary">Open the Appliance What-If →</Link>
          </div>
        </section>
      )}
    </div>
  );
}
