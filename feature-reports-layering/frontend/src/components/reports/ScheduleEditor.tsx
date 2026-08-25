import type { Cadence, ScheduleEntry } from "../../types/reports";

const CADENCES: Cadence[] = ["hourly", "daily", "weekly", "monthly", "cron"];
const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function defaultEntry(): ScheduleEntry {
  return { cadence: "daily", time: "08:00", enabled: true };
}

/** Human summary of a schedule entry, e.g. "Weekly · Mon · 08:00". */
export function describeSchedule(s: ScheduleEntry): string {
  const t = s.time || "—";
  switch (s.cadence) {
    case "hourly":
      return "Hourly";
    case "daily":
      return `Daily · ${t}`;
    case "weekly":
      return `Weekly · ${DOW[s.day_of_week ?? 0]} · ${t}`;
    case "monthly":
      return `Monthly · day ${s.day_of_month ?? 1} · ${t}`;
    case "cron":
      return `Cron · ${s.cron || "—"}`;
    default:
      return s.cadence;
  }
}

/** CRUD editor for saved schedule entries. Stored only — no runner yet. */
export function ScheduleEditor({
  value,
  onChange,
}: {
  value: ScheduleEntry[];
  onChange: (next: ScheduleEntry[]) => void;
}) {
  const patch = (i: number, p: Partial<ScheduleEntry>) =>
    onChange(value.map((s, idx) => (idx === i ? { ...s, ...p } : s)));

  return (
    <div className="rl-sched">
      {value.length === 0 && (
        <span className="rl-hint">No schedules — add one below.</span>
      )}
      {value.map((s, i) => (
        <div className="rl-sched-row" key={i}>
          <input
            type="checkbox"
            checked={s.enabled !== false}
            onChange={(e) => patch(i, { enabled: e.target.checked })}
            title="Enabled"
          />
          <select
            value={s.cadence}
            onChange={(e) => patch(i, { cadence: e.target.value as Cadence })}
          >
            {CADENCES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          {(s.cadence === "daily" ||
            s.cadence === "weekly" ||
            s.cadence === "monthly") && (
            <input
              type="time"
              value={s.time ?? "08:00"}
              onChange={(e) => patch(i, { time: e.target.value })}
            />
          )}
          {s.cadence === "weekly" && (
            <select
              value={s.day_of_week ?? 0}
              onChange={(e) => patch(i, { day_of_week: Number(e.target.value) })}
            >
              {DOW.map((d, idx) => (
                <option key={d} value={idx}>
                  {d}
                </option>
              ))}
            </select>
          )}
          {s.cadence === "monthly" && (
            <input
              type="number"
              min={1}
              max={31}
              value={s.day_of_month ?? 1}
              onChange={(e) => patch(i, { day_of_month: Number(e.target.value) })}
              title="Day of month"
              style={{ width: 64 }}
            />
          )}
          {s.cadence === "cron" && (
            <input
              placeholder="0 8 * * *"
              value={s.cron ?? ""}
              onChange={(e) => patch(i, { cron: e.target.value })}
              style={{ flex: 1, minWidth: 120 }}
            />
          )}

          <input
            className="rl-sched-label"
            placeholder="Label (optional)"
            value={s.label ?? ""}
            onChange={(e) => patch(i, { label: e.target.value })}
          />
          <button
            type="button"
            className="rl-sched-remove"
            onClick={() => onChange(value.filter((_, idx) => idx !== i))}
            aria-label="Remove schedule"
          >
            ✕
          </button>
        </div>
      ))}
      <button
        type="button"
        className="rl-btn"
        onClick={() => onChange([...value, defaultEntry()])}
      >
        + Add schedule
      </button>
    </div>
  );
}
