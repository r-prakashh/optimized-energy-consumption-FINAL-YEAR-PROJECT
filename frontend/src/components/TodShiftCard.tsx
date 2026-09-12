import type { TodShiftOpportunity } from "../api/client";
import { ApplianceIcon } from "./ApplianceIcons";

interface Props {
  opportunities: TodShiftOpportunity[];
  totalSaving: number;
  durationDays: number;
}

export function TodShiftCard({ opportunities, totalSaving, durationDays }: Props) {
  if (opportunities.length === 0) return null;

  return (
    <div className="tod-card">
      <div className="tod-header">
        <span className="tod-badge">Simulated</span>
        <h3>Time-of-day shift opportunity</h3>
      </div>
      <p className="tod-sub">
        TNEB doesn't bill time-of-day pricing today, but if it did — shifting
        these unattended loads to off-peak hours (11pm–6am) would save an
        estimated <strong>₹{totalSaving.toFixed(2)}</strong> over{" "}
        {durationDays} days.
      </p>
      <div className="tod-list">
        {opportunities.map((o) => (
          <div className="tod-row" key={o.category}>
            <ApplianceIcon category={o.category} />
            <span className="tod-label">{o.label}</span>
            <span className="tod-saving">
              −₹{(o.estimated_saving_per_day * durationDays).toFixed(2)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
