import {
  Area,
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BillAnalysis } from "../api/client";
import { monthLabel } from "../utils/format";

interface Row {
  name: string;
  actual?: number;
  anomaly?: boolean;
  forecast?: number;
  band?: [number, number];
}

export function BillTrendChart({ analysis }: { analysis: BillAnalysis }) {
  const rows: Row[] = analysis.history.map((h) => ({
    name: monthLabel(h.label),
    actual: h.kwh,
    anomaly: h.is_anomaly,
  }));
  // Start the forecast line at the last actual month so the two connect.
  if (rows.length) {
    const last = rows[rows.length - 1];
    last.forecast = last.actual;
    last.band = [last.actual!, last.actual!];
  }
  analysis.forecast.forEach((f) =>
    rows.push({ name: monthLabel(f.label), forecast: f.kwh, band: [f.lower, f.upper] })
  );

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={rows} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
        <XAxis dataKey="name" tick={{ fontSize: 11, fill: "var(--text-secondary)" }} />
        <YAxis tick={{ fontSize: 11, fill: "var(--text-secondary)" }} unit=" kWh" width={70} />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.04)" }}
          contentStyle={{ fontSize: 12, background: "#17181c", border: "1px solid #2a2b31", borderRadius: 8 }}
          formatter={(value, name) => {
            if (Array.isArray(value)) return [`${value[0]}–${value[1]} kWh`, "80% range"];
            return [`${value} kWh`, name];
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area
          dataKey="band"
          name="Forecast range"
          stroke="none"
          fill="#ffd93d"
          fillOpacity={0.15}
          isAnimationActive={false}
          legendType="square"
        />
        <Bar dataKey="actual" name="Monthly usage (from bills)" fill="#e50914" radius={[6, 6, 0, 0]} maxBarSize={38}>
          {rows.map((r, i) => (
            <Cell key={i} fill={r.anomaly ? "#ff7a45" : "#e50914"} />
          ))}
        </Bar>
        <Line
          dataKey="forecast"
          name="Forecast"
          stroke="#ffd93d"
          strokeWidth={2.5}
          strokeDasharray="6 4"
          dot={{ r: 4, fill: "#ffd93d" }}
          connectNulls
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
