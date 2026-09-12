import type { ApplianceResult } from "../api/client";
import { ApplianceIcon } from "./ApplianceIcons";

interface Props {
  appliances: ApplianceResult[];
}

export function ApplianceCompareBars({ appliances }: Props) {
  const maxHours = Math.max(...appliances.map((a) => a.original_hours), 1);

  return (
    <div className="compare-list">
      {appliances.map((a) => (
        <div className="compare-row" key={a.category}>
          <div className="compare-icon">
            <ApplianceIcon category={a.category} />
          </div>
          <div className="compare-body">
            <div className="compare-top">
              <span className="compare-label">{a.label}</span>
              <span className="compare-hours">
                {a.reduced ? (
                  <>
                    <span className="was">{a.original_hours}h</span> →{" "}
                    <span className="now">{a.recommended_hours}h</span>
                  </>
                ) : (
                  <span className="now">{a.recommended_hours}h</span>
                )}
              </span>
            </div>
            <div className="compare-track">
              <div
                className="compare-bar original"
                style={{ width: `${(a.original_hours / maxHours) * 100}%` }}
              />
              <div
                className={`compare-bar recommended ${a.reduced ? "reduced" : ""}`}
                style={{ width: `${(a.recommended_hours / maxHours) * 100}%` }}
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
