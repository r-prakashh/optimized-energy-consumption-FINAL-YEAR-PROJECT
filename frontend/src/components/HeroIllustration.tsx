/**
 * Abstract animated backdrop for the hero — soft drifting gradient blobs
 * (CSS, in .hero-bg) plus a glowing energy-waveform line (SVG here). No
 * external image assets, no literal icon illustration — a more premium,
 * less cluttered "modern SaaS" mesh-gradient look.
 */

/** Builds a smooth cubic-bezier wave path from evenly-spaced points, so the
 * `d` string is always syntactically valid (each C segment gets its own
 * full 6-number tuple — no shorthand S commands to miscount). */
function buildWavePath(points: number[], width: number, baseY: number, amplitude: number): string {
  const step = width / (points.length - 1);
  const coords = points.map((p, i) => ({ x: i * step, y: baseY + p * amplitude }));

  let d = `M${coords[0].x},${coords[0].y}`;
  for (let i = 0; i < coords.length - 1; i++) {
    const p0 = coords[i];
    const p1 = coords[i + 1];
    const cpX = (p0.x + p1.x) / 2;
    d += ` C${cpX},${p0.y} ${cpX},${p1.y} ${p1.x},${p1.y}`;
  }
  return d;
}

const WIDTH = 1400;
const WAVE_A = buildWavePath([0, -1, 1, -0.6, 1.4, -1.2, 0.8, -0.4, 0], WIDTH, 400, 90);
const WAVE_A2 = buildWavePath([0.1, -0.9, 1.1, -0.5, 1.3, -1.3, 0.7, -0.5, 0.1], WIDTH, 395, 85);
const WAVE_B = buildWavePath([0, 0.9, -1.2, 0.6, -1.4, 1.1, -0.7, 0.3, 0], WIDTH, 470, 75);

export function HeroIllustration() {
  return (
    <svg
      viewBox="0 0 1400 800"
      className="hero-illustration"
      xmlns="http://www.w3.org/2000/svg"
      preserveAspectRatio="xMidYMid slice"
    >
      <defs>
        <filter id="waveGlow" x="-20%" y="-200%" width="140%" height="500%">
          <feGaussianBlur stdDeviation="6" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <linearGradient id="waveFade" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#e50914" stopOpacity="0" />
          <stop offset="15%" stopColor="#e50914" stopOpacity="0.9" />
          <stop offset="85%" stopColor="#ff8a3d" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#ff8a3d" stopOpacity="0" />
        </linearGradient>
        <pattern id="grid" width="46" height="46" patternUnits="userSpaceOnUse">
          <path d="M46 0H0V46" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="1" />
        </pattern>
      </defs>

      <rect width="1400" height="800" fill="url(#grid)" />

      <g filter="url(#waveGlow)" opacity="0.85">
        <path fill="none" stroke="url(#waveFade)" strokeWidth="3" strokeLinecap="round" d={WAVE_A}>
          <animate attributeName="d" dur="9s" repeatCount="indefinite" values={`${WAVE_A};${WAVE_A2};${WAVE_A}`} />
        </path>
        <path
          fill="none"
          stroke="url(#waveFade)"
          strokeWidth="2"
          strokeOpacity="0.4"
          strokeLinecap="round"
          d={WAVE_B}
        />
      </g>

      {/* faint horizon glow line */}
      <line x1="0" y1="720" x2="1400" y2="720" stroke="rgba(229,9,20,0.3)" strokeWidth="1" />
    </svg>
  );
}
