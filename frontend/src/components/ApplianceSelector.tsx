import type { ApplianceCatalogEntry, ApplianceSpecs } from "../api/client";
import { ApplianceIcon } from "./ApplianceIcons";

export interface SelectedAppliance {
  hours: number;
  specs: ApplianceSpecs;
}

interface Props {
  catalog: ApplianceCatalogEntry[];
  selected: Record<string, SelectedAppliance>;
  onToggle: (category: string, checked: boolean) => void;
  onHoursChange: (category: string, hours: number) => void;
  onSpecChange: (category: string, key: string, value: string | number | boolean) => void;
}

const FLEXIBILITY_COLOR: Record<string, string> = {
  none: "#8a8f98",
  low: "#4c8bf5",
  medium: "#f5c542",
  high: "#e5484d",
};

export function ApplianceSelector({
  catalog,
  selected,
  onToggle,
  onHoursChange,
  onSpecChange,
}: Props) {
  return (
    <div className="appliance-grid">
      {catalog.map((appliance) => {
        const entry = selected[appliance.category];
        const isChecked = !!entry;
        return (
          <div
            key={appliance.category}
            className={`appliance-card ${isChecked ? "active" : ""}`}
            onClick={() => !isChecked && onToggle(appliance.category, true)}
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
              {isChecked && (
                <button
                  className="remove-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggle(appliance.category, false);
                  }}
                  aria-label={`Remove ${appliance.label}`}
                >
                  ×
                </button>
              )}
            </div>

            {isChecked && (
              <div onClick={(e) => e.stopPropagation()}>
                <div className="appliance-hours">
                  <input
                    type="range"
                    min={appliance.min_hours}
                    max={appliance.max_hours}
                    step={0.5}
                    value={entry.hours}
                    onChange={(e) => onHoursChange(appliance.category, Number(e.target.value))}
                  />
                  <span className="hours-value">{entry.hours} hrs/day</span>
                </div>

                {appliance.specs.length > 0 && (
                  <div className="spec-fields">
                    {appliance.specs.map((field) => (
                      <label className="spec-field" key={field.key}>
                        <span>{field.label}</span>
                        {field.type === "boolean" ? (
                          <select
                            value={String(entry.specs[field.key] ?? field.default)}
                            onChange={(e) =>
                              onSpecChange(appliance.category, field.key, e.target.value === "true")
                            }
                          >
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                          </select>
                        ) : (
                          <select
                            value={String(entry.specs[field.key] ?? field.default)}
                            onChange={(e) => {
                              const raw = e.target.value;
                              const numeric = Number(raw);
                              onSpecChange(
                                appliance.category,
                                field.key,
                                Number.isNaN(numeric) ? raw : numeric
                              );
                            }}
                          >
                            {field.options.map((opt) => (
                              <option key={String(opt)} value={String(opt)}>
                                {String(opt).replace(/_/g, " ")}
                                {field.unit ? ` ${field.unit}` : ""}
                              </option>
                            ))}
                          </select>
                        )}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
