import type { CSSProperties, JSX } from "react";

/**
 * Filled, two-tone illustrations per appliance category — a step up from
 * thin line icons toward an actual "product image" feel, while staying
 * inline SVG (zero external requests, no licensing concerns, crisp in any
 * theme, instant load). Each has a colored backdrop plate plus a glyph in
 * a complementary tone, in the style of modern app iconography.
 */
const PALETTE: Record<string, { bg: string; fg: string; accent: string }> = {
  air_conditioner: { bg: "#1c3a5e", fg: "#eaf4ff", accent: "#5ec8f8" },
  fan: { bg: "#2a2a1c", fg: "#fff6df", accent: "#f5c542" },
  television: { bg: "#1a1a24", fg: "#dfe6ff", accent: "#7a8cff" },
  lighting: { bg: "#3a2e10", fg: "#fff3d0", accent: "#ffc233" },
  refrigerator: { bg: "#12333b", fg: "#e4faff", accent: "#4fd6e8" },
  washing_machine: { bg: "#12305a", fg: "#e7f0ff", accent: "#5b8dff" },
  computer: { bg: "#241c3a", fg: "#ecdfff", accent: "#a074ff" },
  microwave: { bg: "#3a1c1c", fg: "#ffe4e0", accent: "#ff7a5c" },
  water_heater: { bg: "#4a1616", fg: "#ffe6e0", accent: "#ff5c4d" },
  motor_pump: { bg: "#123a2e", fg: "#e2fff2", accent: "#3ddc9a" },
};

const glyphs: Record<string, JSX.Element> = {
  air_conditioner: (
    <>
      <rect x="7" y="15" width="34" height="14" rx="3.5" fill="var(--fg)" />
      <rect x="10.5" y="19.5" width="2.5" height="5" rx="1.25" fill="var(--bg)" />
      <rect x="16" y="19.5" width="2.5" height="5" rx="1.25" fill="var(--bg)" />
      <rect x="21.5" y="19.5" width="2.5" height="5" rx="1.25" fill="var(--bg)" />
      <rect x="27" y="19.5" width="2.5" height="5" rx="1.25" fill="var(--bg)" />
      <rect x="32.5" y="19.5" width="2.5" height="5" rx="1.25" fill="var(--bg)" />
      <path d="M11 32c0 2 2 3 2 5M17 32c0 3 2.5 4.5 2.5 7M27.5 32c0 3-2.5 4.5-2.5 7M34 32c0 2-2 3-2 5"
        stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" fill="none" />
    </>
  ),
  fan: (
    <>
      <circle cx="24" cy="20" r="3.4" fill="var(--accent)" />
      <path d="M24 17c-2-5-1-10 3.5-12 4-1.6 7.5 1 6.5 4.5-1 3.6-5.5 5.5-10 7.5Z" fill="var(--fg)" />
      <path d="M26.6 19.6c4.6-2 9.6-1 11.5 3 1.6 3.6-1 7-4.5 6-3.6-1-5.5-5-7-9Z" fill="var(--fg)" opacity="0.85" />
      <path d="M21.4 22.4c-4.6 2-9.6 1-11.5-3-1.6-3.6 1-7 4.5-6 3.6 1 5.5 5 7 9Z" fill="var(--fg)" opacity="0.7" />
      <rect x="22.5" y="30" width="3" height="10" rx="1.5" fill="var(--fg)" opacity="0.5" />
    </>
  ),
  television: (
    <>
      <rect x="6" y="10" width="36" height="21" rx="2.5" fill="var(--fg)" />
      <rect x="9" y="13" width="30" height="15" rx="1" fill="var(--bg)" />
      <path d="M12 17h14M12 21h9" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
      <rect x="20" y="33" width="8" height="3" rx="1.5" fill="var(--fg)" opacity="0.6" />
    </>
  ),
  lighting: (
    <>
      <path
        d="M24 6c-7 0-12 5-12 12 0 5 3 8 5 11 1.5 2 2 3 2 5h10c0-2 .5-3 2-5 2-3 5-6 5-11 0-7-5-12-12-12Z"
        fill="var(--fg)"
      />
      <path d="M20 21l3-6 2 3 3-4" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <rect x="19" y="36" width="10" height="3" rx="1.5" fill="var(--fg)" opacity="0.7" />
      <rect x="20" y="40" width="8" height="2.5" rx="1.25" fill="var(--fg)" opacity="0.5" />
    </>
  ),
  refrigerator: (
    <>
      <rect x="11" y="4" width="26" height="40" rx="3.5" fill="var(--fg)" />
      <rect x="11" y="18" width="26" height="1.5" fill="var(--bg)" />
      <rect x="14.5" y="8" width="2.5" height="6" rx="1.25" fill="var(--accent)" />
      <rect x="14.5" y="23" width="2.5" height="6" rx="1.25" fill="var(--accent)" />
    </>
  ),
  washing_machine: (
    <>
      <rect x="6" y="6" width="36" height="36" rx="5" fill="var(--fg)" />
      <rect x="6" y="6" width="36" height="7" rx="5" fill="var(--fg)" />
      <circle cx="12" cy="9.5" r="1.3" fill="var(--bg)" />
      <circle cx="17" cy="9.5" r="1.3" fill="var(--bg)" />
      <circle cx="24" cy="27" r="10.5" fill="var(--bg)" />
      <circle cx="24" cy="27" r="7.5" fill="var(--accent)" opacity="0.85" />
      <path d="M20 27a4 4 0 0 0 7 2.6" stroke="var(--fg)" strokeWidth="2" strokeLinecap="round" fill="none" />
    </>
  ),
  computer: (
    <>
      <rect x="6" y="8" width="36" height="24" rx="2.5" fill="var(--fg)" />
      <rect x="9" y="11" width="30" height="18" rx="1" fill="var(--bg)" />
      <path d="M13 16h20M13 20h14M13 24h17" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" />
      <rect x="17" y="35" width="14" height="3" rx="1.5" fill="var(--fg)" opacity="0.6" />
    </>
  ),
  microwave: (
    <>
      <rect x="4" y="11" width="40" height="26" rx="3.5" fill="var(--fg)" />
      <rect x="8" y="15" width="21" height="18" rx="1.5" fill="var(--bg)" />
      <rect x="10.5" y="17.5" width="16" height="13" rx="1" fill="var(--accent)" opacity="0.55" />
      <circle cx="35.5" cy="20" r="2.2" fill="var(--accent)" />
      <rect x="32" y="26" width="7" height="2.2" rx="1.1" fill="var(--bg)" />
      <rect x="32" y="30" width="7" height="2.2" rx="1.1" fill="var(--bg)" />
    </>
  ),
  water_heater: (
    <>
      <rect x="13" y="5" width="22" height="37" rx="9" fill="var(--fg)" />
      <path
        d="M20 15c0 2-2.5 2.4-2.5 4.5s2.5 2.5 2.5 4.5-2.5 2.5-2.5 4.5 2.5 2.5 2.5 4.5"
        stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" fill="none"
      />
      <path
        d="M29 15c0 2-2.5 2.4-2.5 4.5s2.5 2.5 2.5 4.5-2.5 2.5-2.5 4.5 2.5 2.5 2.5 4.5"
        stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" fill="none"
      />
      <circle cx="24" cy="11" r="2" fill="var(--bg)" />
    </>
  ),
  motor_pump: (
    <>
      <circle cx="19" cy="24" r="11" fill="var(--fg)" />
      <circle cx="19" cy="24" r="6.5" fill="var(--bg)" />
      <path d="M19 20v4l3 2" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <rect x="29" y="21" width="11" height="6" rx="2" fill="var(--fg)" />
      <path d="M11 39c3-3 7-3 10 0s7 3 10 0" stroke="var(--accent)" strokeWidth="2.2" strokeLinecap="round" fill="none" />
    </>
  ),
};

const fallbackGlyph = (
  <>
    <rect x="8" y="8" width="32" height="32" rx="7" fill="var(--fg)" />
    <path d="M24 16v10l6 4" stroke="var(--bg)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
  </>
);

export function ApplianceIcon({ category }: { category: string }) {
  const colors = PALETTE[category] ?? { bg: "#1c1c22", fg: "#eee", accent: "#e50914" };
  const glyph = glyphs[category] ?? fallbackGlyph;

  return (
    <span
      className="appliance-icon"
      style={
        {
          background: colors.bg,
          "--fg": colors.fg,
          "--bg": colors.bg,
          "--accent": colors.accent,
        } as CSSProperties
      }
    >
      <svg viewBox="0 0 48 48">{glyph}</svg>
    </span>
  );
}
