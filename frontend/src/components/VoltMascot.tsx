import { useId } from "react";

interface Props {
  size?: number;
  mood?: "idle" | "thinking" | "happy";
  wave?: boolean;
  className?: string;
}

/**
 * Volt — WattWise's assistant mascot: a round little power-orb with a
 * lightning-bolt crest. Bobs gently, blinks, waves hello, and squints its
 * eyes while "thinking". Pure inline SVG + CSS animations (see App.css
 * `.volt-*`), so it costs no image requests and scales to any size.
 */
export function VoltMascot({ size = 56, mood = "idle", wave = false, className = "" }: Props) {
  const uid = useId().replace(/:/g, "");
  const body = `volt-body-${uid}`;
  const crest = `volt-crest-${uid}`;
  const glow = `volt-glow-${uid}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      className={`volt volt-${mood} ${className}`}
      role="img"
      aria-label="Volt, the WattWise assistant"
    >
      <defs>
        <radialGradient id={body} cx="40%" cy="35%" r="70%">
          <stop offset="0%" stopColor="#fff6c2" />
          <stop offset="45%" stopColor="#ffd93d" />
          <stop offset="100%" stopColor="#ff9f1c" />
        </radialGradient>
        <linearGradient id={crest} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#fffbe0" />
          <stop offset="100%" stopColor="#ffc93c" />
        </linearGradient>
        <radialGradient id={glow} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ffd93d" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#ffd93d" stopOpacity="0" />
        </radialGradient>
      </defs>

      <circle cx="60" cy="66" r="56" fill={`url(#${glow})`} className="volt-halo" />

      <g className="volt-bob">
        {/* sparks */}
        <g className="volt-sparks" stroke="#ffe066" strokeWidth="3" strokeLinecap="round">
          <path d="M14 46 l-7 -4" />
          <path d="M12 62 h-8" />
          <path d="M106 46 l7 -4" />
          <path d="M108 62 h8" />
        </g>

        {/* lightning crest */}
        <path
          d="M64 4 L46 34 H58 L52 52 L76 22 H63 L70 4 Z"
          fill={`url(#${crest})`}
          stroke="#e8890c"
          strokeWidth="2.5"
          strokeLinejoin="round"
          className="volt-crest"
        />

        {/* left arm */}
        <path d="M24 78 q-10 2 -12 -8" stroke="#e8890c" strokeWidth="5" strokeLinecap="round" fill="none" />
        {/* right arm (waves) */}
        <g className={wave ? "volt-wave" : ""} style={{ transformOrigin: "94px 76px" }}>
          <path d="M94 76 q12 -4 12 -16" stroke="#e8890c" strokeWidth="5" strokeLinecap="round" fill="none" />
          <circle cx="106" cy="58" r="4.5" fill="#ffd93d" stroke="#e8890c" strokeWidth="2" />
        </g>

        {/* body */}
        <circle cx="60" cy="72" r="38" fill={`url(#${body})`} stroke="#e8890c" strokeWidth="3" />
        <ellipse cx="46" cy="56" rx="10" ry="6" fill="#fffbe6" opacity="0.7" transform="rotate(-25 46 56)" />

        {/* face */}
        <g className="volt-eyes">
          {mood === "happy" ? (
            <>
              <path d="M40 72 q7 -9 14 0" stroke="#1d1b2f" strokeWidth="4" strokeLinecap="round" fill="none" />
              <path d="M66 72 q7 -9 14 0" stroke="#1d1b2f" strokeWidth="4" strokeLinecap="round" fill="none" />
            </>
          ) : (
            <>
              <ellipse cx="47" cy="70" rx="7" ry={mood === "thinking" ? 4 : 9} fill="#1d1b2f" />
              <ellipse cx="73" cy="70" rx="7" ry={mood === "thinking" ? 4 : 9} fill="#1d1b2f" />
              <circle cx="49.5" cy={mood === "thinking" ? 68.5 : 66} r="2.6" fill="#fff" />
              <circle cx="75.5" cy={mood === "thinking" ? 68.5 : 66} r="2.6" fill="#fff" />
            </>
          )}
        </g>
        <ellipse cx="36" cy="84" rx="6" ry="3.6" fill="#ff7a7a" opacity="0.55" />
        <ellipse cx="84" cy="84" rx="6" ry="3.6" fill="#ff7a7a" opacity="0.55" />
        {mood === "thinking" ? (
          <ellipse cx="60" cy="90" rx="4" ry="3" fill="#7a2e0e" />
        ) : (
          <path d="M51 86 q9 9 18 0" stroke="#7a2e0e" strokeWidth="3.5" strokeLinecap="round" fill="#c2410c" />
        )}

        {/* little feet */}
        <ellipse cx="48" cy="111" rx="8" ry="4" fill="#e8890c" />
        <ellipse cx="72" cy="111" rx="8" ry="4" fill="#e8890c" />
      </g>
    </svg>
  );
}
