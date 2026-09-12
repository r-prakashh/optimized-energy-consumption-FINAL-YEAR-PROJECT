import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  forecastDailyKwh: number[];
}

export function ForecastChart({ forecastDailyKwh }: Props) {
  const data = forecastDailyKwh.map((kwh, i) => ({
    day: `Day ${i + 1}`,
    kwh: Number(kwh.toFixed(2)),
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="kwhGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4c8bf5" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#4c8bf5" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
        <XAxis dataKey="day" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 11 }} unit=" kWh" width={60} />
        <Tooltip
          formatter={(value) => [`${value} kWh`, "Projected"]}
          contentStyle={{ fontSize: 12 }}
        />
        <Area
          type="monotone"
          dataKey="kwh"
          stroke="#4c8bf5"
          strokeWidth={2}
          fill="url(#kwhGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
