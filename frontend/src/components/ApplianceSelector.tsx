import type { ApplianceCatalogEntry } from "../api/client";
import { ApplianceIcon } from "./ApplianceIcons";

interface Props {
  catalog: ApplianceCatalogEntry[];
  selected: Record<string, number>;
  onChange: (category: string, hours: number | null) => void;
}

const FLEXIBILITY_COLOR: Record<string, string> = {
  none: "#8a8f98",
  low: "#4c8bf5",
  medium: "#f5c542",
  high: "#e5484d",
};

export function ApplianceSelector({ catalog, selected, onChange }: Props) {
  return (
    <div className="appliance-grid">
      {catalog.map((appliance) => {
        const isChecked = appliance.category in selected;
        return (
          <div
            key={appliance.category}
            className={`appliance-card ${isChecked ? "active" : ""}`}
            onClick={() =>
              onChange(
                appliance.category,
                isChecked ? null : Math.min(4, appliance.max_hours)
              )
            }
          >
            <div className="appliance-card-header">
              <ApplianceIcon category={appliance.category} />
              <div className="appliance-card-title">
                <span className="appliance-label">{appliance.label}</span>
                <span className="appliance-meta">{appliance.avg_watts} W avg</span>
              </div>
              <span
                className="flex-badge"
                style={{ background: FLEXIBILITY_COLOR[appliance.flexibility] }}
                title={`${appliance.flexibility} flexibility`}
              >
                {appliance.flexibility}
              </span>
            </div>
            {isChecked && (
              <div
                className="appliance-hours"
                onClick={(e) => e.stopPropagation()}
              >
                <input
                  type="range"
                  min={appliance.min_hours}
                  max={appliance.max_hours}
                  step={0.5}
                  value={selected[appliance.category]}
                  onChange={(e) => onChange(appliance.category, Number(e.target.value))}
                />
                <span className="hours-value">
                  {selected[appliance.category]} hrs/day
                </span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
