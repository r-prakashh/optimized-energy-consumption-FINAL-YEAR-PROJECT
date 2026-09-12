/**
 * Custom illustrated hero scene (no external image assets — self-contained
 * inline SVG, zero licensing/hosting concerns): a glowing central budget
 * meter with appliance chips orbiting it over a night skyline, rendered
 * full-bleed and symmetric so it reads clearly behind centered hero copy.
 */
export function HeroIllustration() {
  return (
    <svg viewBox="0 0 1400 800" className="hero-illustration" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
      <defs>
        <radialGradient id="glow" cx="50%" cy="46%" r="50%">
          <stop offset="0%" stopColor="#ff2a35" stopOpacity="0.55" />
          <stop offset="45%" stopColor="#e50914" stopOpacity="0.22" />
          <stop offset="100%" stopColor="#e50914" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="glow2" cx="50%" cy="46%" r="30%">
          <stop offset="0%" stopColor="#ff8a3d" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#ff8a3d" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="dialGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#33343b" />
          <stop offset="100%" stopColor="#141417" />
        </linearGradient>
        <pattern id="grid" width="44" height="44" patternUnits="userSpaceOnUse">
          <path d="M44 0H0V44" fill="none" stroke="rgba(255,255,255,0.055)" strokeWidth="1" />
        </pattern>
      </defs>

      <rect width="1400" height="800" fill="#0a0a0c" />
      <rect width="1400" height="800" fill="url(#grid)" />
      <circle cx="700" cy="360" r="480" fill="url(#glow)" />
      <circle cx="700" cy="360" r="220" fill="url(#glow2)" />

      {/* night skyline across full width */}
      <g opacity="0.5">
        {[
          [30, 560, 80, 200], [130, 610, 60, 150], [210, 520, 90, 240],
          [1060, 540, 85, 220], [1170, 600, 60, 160], [1260, 500, 100, 260],
          [340, 640, 55, 120], [960, 630, 55, 130],
        ].map(([x, y, w, h], i) => (
          <rect key={i} x={x} y={y} width={w} height={h} fill={i % 2 ? "#17181c" : "#141417"} />
        ))}
        {Array.from({ length: 40 }).map((_, i) => {
          const x = 40 + ((i * 37) % 1320);
          const y = 540 + ((i * 53) % 220);
          return <rect key={i} x={x} y={y} width="7" height="9" fill="#f5c542" opacity={0.25 + (i % 4) * 0.12} />;
        })}
      </g>

      <line x1="0" y1="720" x2="1400" y2="720" stroke="rgba(229,9,20,0.45)" strokeWidth="1.5" />

      {/* orbit ring */}
      <circle cx="700" cy="360" r="230" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1" strokeDasharray="2 6" />

      {/* energy flow lines from appliance chips to central meter */}
      <g fill="none" stroke="#e50914" strokeWidth="1.5" strokeDasharray="4 5" opacity="0.5">
        <path d="M520 180 C 580 230, 630 280, 660 320" />
        <path d="M880 180 C 820 230, 770 280, 740 320" />
        <path d="M480 560 C 550 500, 610 440, 655 390" />
        <path d="M920 560 C 850 500, 790 440, 745 390" />
        <path d="M340 360 C 450 360, 540 360, 610 360" />
        <path d="M1060 360 C 950 360, 860 360, 790 360" />
      </g>

      {/* appliance chips arranged in an orbit around the meter */}
      {[
        { x: 484, y: 144, bg: "#1c3a5e" },
        { x: 844, y: 144, bg: "#2a2a1c" },
        { x: 304, y: 324, bg: "#12305a" },
        { x: 1024, y: 324, bg: "#3a1c1c" },
        { x: 444, y: 524, bg: "#3a2e10" },
        { x: 884, y: 524, bg: "#123a2e" },
      ].map((c, i) => (
        <g key={i} transform={`translate(${c.x},${c.y})`}>
          <rect width="72" height="72" rx="18" fill={c.bg} opacity="0.9" />
          <circle cx="36" cy="36" r="26" fill="rgba(255,255,255,0.08)" />
          <circle cx="36" cy="36" r="6" fill="#fff" opacity="0.9" />
        </g>
      ))}

      {/* central smart meter dial */}
      <g transform="translate(700,360)">
        <circle r="130" fill="url(#dialGrad)" stroke="#3a3b42" strokeWidth="2" />
        <circle r="130" fill="none" stroke="#e50914" strokeWidth="2.5" strokeDasharray="7 9" opacity="0.7">
          <animateTransform attributeName="transform" type="rotate" from="0 0 0" to="360 0 0" dur="36s" repeatCount="indefinite" />
        </circle>
        <circle r="98" fill="#0f0f12" />
        {Array.from({ length: 30 }).map((_, i) => {
          const angle = (i / 30) * Math.PI * 2;
          const r1 = 82, r2 = 92;
          return (
            <line
              key={i}
              x1={Math.cos(angle) * r1} y1={Math.sin(angle) * r1}
              x2={Math.cos(angle) * r2} y2={Math.sin(angle) * r2}
              stroke="#ff3b44" strokeWidth="2.5"
              opacity={i % 3 === 0 ? 1 : 0.35}
            />
          );
        })}
        <text x="0" y="-8" textAnchor="middle" fontSize="38" fontWeight="800" fill="#ffffff" fontFamily="Inter, sans-serif">₹</text>
        <text x="0" y="30" textAnchor="middle" fontSize="15" fontWeight="700" fill="#c7c8cf" fontFamily="Inter, sans-serif" letterSpacing="2">
          BUDGET
        </text>
      </g>
    </svg>
  );
}
