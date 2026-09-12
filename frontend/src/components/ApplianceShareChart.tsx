import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import type { ApplianceResult } from "../api/client";

interface Props {
  appliances: ApplianceResult[];
}

const COLORS = ["#e50914", "#f6121d", "#ff6b57", "#ff9770", "#ffb562", "#ffd166", "#8a0611", "#c9184a"];

export function ApplianceShareChart({ appliances }: Props) {
  const data = appliances
    .filter((a) => a.daily_kwh > 0)
    .map((a) => ({ name: a.label, value: Number(a.daily_kwh.toFixed(3)) }));

  if (data.length === 0) {
    return <p className="empty-state">No consumption to visualize yet.</p>;
  }

  return (
    <div className="donut-wrap">
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={2}
            strokeWidth={0}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [`${value} kWh/day`, name]}
            contentStyle={{ fontSize: 12 }}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="donut-legend">
        {data.map((d, i) => (
          <div className="donut-legend-item" key={d.name}>
            <span className="donut-swatch" style={{ background: COLORS[i % COLORS.length] }} />
            <span className="donut-legend-label">{d.name}</span>
            <span className="donut-legend-value">{d.value} kWh</span>
          </div>
        ))}
      </div>
    </div>
  );
}
