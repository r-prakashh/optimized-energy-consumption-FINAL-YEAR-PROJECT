import type { JSX } from "react";

/**
 * Hand-tuned line icons per appliance category — kept as inline SVG (no
 * external image requests, no licensing concerns, crisp at any size/theme).
 */
const icons: Record<string, JSX.Element> = {
  air_conditioner: (
    <svg viewBox="0 0 48 48" fill="none">
      <rect x="4" y="14" width="40" height="16" rx="4" stroke="currentColor" strokeWidth="2.2" />
      <path d="M10 24h4M18 24h4M26 24h4M34 24h4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M10 34c0 2 1.5 4 3 4M18 34c0 3 2 5 3 5M27 34c0 3-2 5-3 5M35 34c0 2-1.5 4-3 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  fan: (
    <svg viewBox="0 0 48 48" fill="none">
      <circle cx="24" cy="24" r="3.2" stroke="currentColor" strokeWidth="2.2" />
      <path
        d="M24 21c-2-5-1-11 4-13 4-1.6 8 1 7 5-1 4-6 6-11 8Z"
        stroke="currentColor" strokeWidth="2" strokeLinejoin="round"
      />
      <path
        d="M27 24c5-2 11-1 13 4 1.6 4-1 8-5 7-4-1-6-6-8-11Z"
        stroke="currentColor" strokeWidth="2" strokeLinejoin="round"
      />
      <path
        d="M21 27c-5 2-11 1-13-4-1.6-4 1-8 5-7 4 1 6 6 8 11Z"
        stroke="currentColor" strokeWidth="2" strokeLinejoin="round"
      />
      <path d="M24 40v3M24 5v3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  television: (
    <svg viewBox="0 0 48 48" fill="none">
      <rect x="5" y="9" width="38" height="24" rx="3" stroke="currentColor" strokeWidth="2.2" />
      <path d="M17 39h14M24 33v6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  ),
  lighting: (
    <svg viewBox="0 0 48 48" fill="none">
      <path
        d="M24 6c-7 0-12 5-12 12 0 5 3 8 5 11 1.5 2 2 3 2 5h10c0-2 .5-3 2-5 2-3 5-6 5-11 0-7-5-12-12-12Z"
        stroke="currentColor" strokeWidth="2.2" strokeLinejoin="round"
      />
      <path d="M19 39h10M20 43h8" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  ),
  refrigerator: (
    <svg viewBox="0 0 48 48" fill="none">
      <rect x="11" y="4" width="26" height="40" rx="3" stroke="currentColor" strokeWidth="2.2" />
      <path d="M11 19h26" stroke="currentColor" strokeWidth="2.2" />
      <path d="M16 9v6M16 24v6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  ),
  washing_machine: (
    <svg viewBox="0 0 48 48" fill="none">
      <rect x="6" y="6" width="36" height="36" rx="4" stroke="currentColor" strokeWidth="2.2" />
      <path d="M6 13h36" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="12" cy="9.5" r="1.4" fill="currentColor" />
      <circle cx="17" cy="9.5" r="1.4" fill="currentColor" />
      <circle cx="24" cy="27" r="9" stroke="currentColor" strokeWidth="2.2" />
      <path d="M20 27a4 4 0 0 0 7 2.6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  computer: (
    <svg viewBox="0 0 48 48" fill="none">
      <rect x="6" y="9" width="36" height="23" rx="2.5" stroke="currentColor" strokeWidth="2.2" />
      <path d="M17 39h14M24 32v7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M13 16h22M13 21h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  microwave: (
    <svg viewBox="0 0 48 48" fill="none">
      <rect x="4" y="12" width="40" height="24" rx="3" stroke="currentColor" strokeWidth="2.2" />
      <rect x="9" y="17" width="20" height="14" rx="1.5" stroke="currentColor" strokeWidth="2" />
      <circle cx="36" cy="21" r="2" stroke="currentColor" strokeWidth="2" />
      <path d="M32 28h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
};

const fallback = (
  <svg viewBox="0 0 48 48" fill="none">
    <rect x="8" y="8" width="32" height="32" rx="6" stroke="currentColor" strokeWidth="2.2" />
    <path d="M24 16v10l6 4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export function ApplianceIcon({ category }: { category: string }) {
  return <span className="appliance-icon">{icons[category] ?? fallback}</span>;
}
