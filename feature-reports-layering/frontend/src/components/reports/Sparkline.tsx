/** A tiny inline trend line built from a numeric series (downsampled). */
export function Sparkline({
  values,
  width = 130,
  height = 30,
}: {
  values: number[];
  width?: number;
  height?: number;
}) {
  const pts = downsample(values, 28);
  if (pts.length < 2) return null;

  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const span = max - min || 1;
  const step = width / (pts.length - 1);
  const y = (v: number) => height - 3 - ((v - min) / span) * (height - 6);

  const line = pts.map((v, i) => `${i * step},${y(v)}`).join(" ");
  const area = `0,${height} ${line} ${width},${height}`;
  // A sparkline shows magnitude over the series, not polarity — a single
  // neutral hue avoids implying "up = good" (false for cost/hours/etc.).
  const stroke = "var(--rl-primary)";

  return (
    <svg
      className="rl-spark"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      width={width}
      height={height}
    >
      <polygon points={area} fill={stroke} opacity={0.1} />
      <polyline
        points={line}
        fill="none"
        stroke={stroke}
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={width} cy={y(pts[pts.length - 1])} r={2} fill={stroke} />
    </svg>
  );
}

/** Reduce an arbitrary-length series to ~n bucket-averaged points. */
function downsample(values: number[], n: number): number[] {
  if (values.length <= n) return values;
  const size = values.length / n;
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    const start = Math.floor(i * size);
    const end = Math.floor((i + 1) * size);
    const slice = values.slice(start, end);
    out.push(slice.reduce((a, b) => a + b, 0) / (slice.length || 1));
  }
  return out;
}
