/** Shimmer placeholders shown while data loads — feels faster than a spinner. */

export function ReportSkeleton() {
  return (
    <div>
      <div className="rl-skel rl-skel-title" />
      <div className="rl-skel rl-skel-sub" />
      <div className="rl-summary" style={{ marginTop: 20 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div className="rl-summary-tile" key={i}>
            <div className="rl-skel rl-skel-line" style={{ width: "50%" }} />
            <div className="rl-skel rl-skel-line" style={{ width: "70%", height: 22 }} />
          </div>
        ))}
      </div>
      <div className="rl-skel rl-skel-table" />
    </div>
  );
}

export function CardGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="rl-grid">
      {Array.from({ length: count }).map((_, i) => (
        <div className="rl-card" key={i}>
          <div className="rl-skel rl-skel-line" style={{ width: "60%", height: 16 }} />
          <div className="rl-skel rl-skel-line" style={{ width: "90%" }} />
          <div className="rl-skel rl-skel-line" style={{ width: "40%" }} />
        </div>
      ))}
    </div>
  );
}
