/**
 * Custom illustrated hero scene (no external image assets — self-contained
 * inline SVG, zero licensing/hosting concerns): a glowing smart-energy-meter
 * centerpiece with appliance chips feeding into it over a night skyline,
 * echoing the "bold text over a moody hero photo" composition style without
 * needing a licensed stock photo. Composition is deliberately weighted to
 * the right two-thirds with a strong opaque fade on the left so hero copy
 * overlaid there stays legible.
 */
export function HeroIllustration() {
  return (
    <svg viewBox="0 0 900 720" className="hero-illustration" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id="glow" cx="63%" cy="42%" r="42%">
          <stop offset="0%" stopColor="#e50914" stopOpacity="0.35" />
          <stop offset="60%" stopColor="#e50914" stopOpacity="0.08" />
          <stop offset="100%" stopColor="#e50914" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="fadeLeft" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#0a0a0c" stopOpacity="1" />
          <stop offset="45%" stopColor="#0a0a0c" stopOpacity="0.85" />
          <stop offset="65%" stopColor="#0a0a0c" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#0a0a0c" stopOpacity="0" />
        </linearGradient>
        <linearGradient id="dialGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2a2b31" />
          <stop offset="100%" stopColor="#141417" />
        </linearGradient>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M40 0H0V40" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
        </pattern>
      </defs>

      <rect width="900" height="720" fill="#0a0a0c" />
      <rect width="900" height="720" fill="url(#grid)" />
      <circle cx="565" cy="300" r="280" fill="url(#glow)" />

      {/* night skyline, right two-thirds only */}
      <g opacity="0.55">
        <rect x="360" y="520" width="70" height="160" fill="#141417" />
        <rect x="440" y="470" width="55" height="210" fill="#17181c" />
        <rect x="505" y="550" width="60" height="130" fill="#141417" />
        <rect x="690" y="500" width="65" height="180" fill="#17181c" />
        <rect x="765" y="540" width="55" height="140" fill="#141417" />
        <rect x="825" y="480" width="50" height="200" fill="#17181c" />
        {[
          [375, 540], [375, 570], [400, 540], [400, 600],
          [455, 495], [455, 530], [480, 560], [480, 600],
          [705, 525], [705, 560], [730, 590],
          [780, 565], [780, 600], [840, 505], [840, 545], [840, 590],
        ].map(([x, y], i) => (
          <rect key={i} x={x} y={y} width="8" height="10" fill="#f5c542" opacity="0.5" />
        ))}
      </g>

      {/* ground glow line */}
      <line x1="340" y1="680" x2="900" y2="680" stroke="rgba(229,9,20,0.4)" strokeWidth="1.5" />

      {/* energy flow lines from appliance chips to central meter */}
      <g fill="none" stroke="#e50914" strokeWidth="1.5" strokeDasharray="4 5" opacity="0.55">
        <path d="M410 200 C 470 230, 505 260, 540 300" />
        <path d="M760 180 C 690 220, 640 260, 595 300" />
        <path d="M420 420 C 480 380, 515 350, 550 320" />
        <path d="M740 440 C 680 400, 640 360, 600 325" />
      </g>

      {/* appliance chips */}
      {[
        { x: 360, y: 165, bg: "#1c3a5e" },
        { x: 730, y: 145, bg: "#2a2a1c" },
        { x: 370, y: 455, bg: "#3a2e10" },
        { x: 710, y: 475, bg: "#12305a" },
      ].map((c, i) => (
        <g key={i} transform={`translate(${c.x},${c.y})`}>
          <rect width="72" height="72" rx="18" fill={c.bg} />
          <circle cx="36" cy="36" r="26" fill="rgba(255,255,255,0.08)" />
          <circle cx="36" cy="36" r="6" fill="#fff" opacity="0.9" />
        </g>
      ))}

      {/* central smart meter dial */}
      <g transform="translate(580,320)">
        <circle r="105" fill="url(#dialGrad)" stroke="#2a2b31" strokeWidth="2" />
        <circle r="105" fill="none" stroke="#e50914" strokeWidth="2" strokeDasharray="6 8" opacity="0.6">
          <animateTransform
            attributeName="transform"
            type="rotate"
            from="0 0 0"
            to="360 0 0"
            dur="40s"
            repeatCount="indefinite"
          />
        </circle>
        <circle r="78" fill="#0f0f12" />
        {Array.from({ length: 24 }).map((_, i) => {
          const angle = (i / 24) * Math.PI * 2;
          const r1 = 66, r2 = 74;
          return (
            <line
              key={i}
              x1={Math.cos(angle) * r1}
              y1={Math.sin(angle) * r1}
              x2={Math.cos(angle) * r2}
              y2={Math.sin(angle) * r2}
              stroke="#e50914"
              strokeWidth="2"
              opacity={i % 3 === 0 ? 0.9 : 0.35}
            />
          );
        })}
        <text x="0" y="-6" textAnchor="middle" fontSize="30" fontWeight="800" fill="#f5f5f7" fontFamily="Inter, sans-serif">
          ₹
        </text>
        <text x="0" y="26" textAnchor="middle" fontSize="13" fontWeight="700" fill="#9a9ba3" fontFamily="Inter, sans-serif" letterSpacing="1.5">
          BUDGET
        </text>
      </g>

      {/* left fade so hero text stays legible when overlaid */}
      <rect width="900" height="720" fill="url(#fadeLeft)" />
    </svg>
  );
}
