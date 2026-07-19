import { useState } from "react";
import type {
  CombineSpec,
  JoinInput,
  SourceInput,
  UploadedDataset,
} from "../../types/reports";
import { uploadDataset } from "../../services/reportsApi";
import { ExpandableTextarea } from "./ExpandableTextarea";

interface Props {
  sources: SourceInput[];
  combine: CombineSpec | null;
  onSourcesChange: (sources: SourceInput[]) => void;
  onCombineChange: (combine: CombineSpec | null) => void;
}

function nextSourceName(existing: SourceInput[]): string {
  for (const c of "abcdefghijklmnopqrstuvwxyz") {
    const name = `source_${c}`;
    if (!existing.some((s) => s.name === name)) return name;
  }
  return `source_${existing.length + 1}`;
}

/** Author editor for a report's data sources (SQL and/or uploaded files) plus
 * how to combine them (join / union). Fully controlled by the parent. */
export function SourceEditor({
  sources,
  combine,
  onSourcesChange,
  onCombineChange,
}: Props) {
  // file_ref -> upload metadata, for showing filename + inferred columns.
  const [uploads, setUploads] = useState<Record<string, UploadedDataset>>({});
  const [busyIdx, setBusyIdx] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  function patchSource(idx: number, patch: Partial<SourceInput>) {
    onSourcesChange(sources.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  }

  function addSource() {
    onSourcesChange([
      ...sources,
      { name: nextSourceName(sources), type: "sql", sql: "" },
    ]);
  }

  function removeSource(idx: number) {
    const next = sources.filter((_, i) => i !== idx);
    onSourcesChange(next);
    if (next.length < 2) onCombineChange(null);
  }

  async function onPickFile(idx: number, file: File | null) {
    if (!file) return;
    setBusyIdx(idx);
    setUploadError(null);
    try {
      const ds = await uploadDataset(file);
      setUploads((m) => ({ ...m, [ds.file_ref]: ds }));
      patchSource(idx, { type: "file", file_ref: ds.file_ref });
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setBusyIdx(null);
    }
  }

  const names = sources.map((s) => s.name);
  const multi = sources.length >= 2;

  function setOp(op: "join" | "union") {
    if (op === "union") {
      onCombineChange({ op: "union", distinct: combine?.distinct ?? false });
    } else {
      onCombineChange({
        op: "join",
        joins: [
          { left: names[0] ?? "", right: names[1] ?? "", on: [["", ""]], how: "inner" },
        ],
      });
    }
  }

  const joins = combine?.op === "join" ? (combine.joins ?? []) : [];

  function patchJoinAt(ji: number, patch: Partial<JoinInput>) {
    if (combine?.op !== "join") return;
    onCombineChange({
      ...combine,
      joins: joins.map((j, i) => (i === ji ? { ...j, ...patch } : j)),
    });
  }
  function patchPairAt(ji: number, pi: number, side: "l" | "r", value: string) {
    const j = joins[ji];
    if (!j) return;
    const on = j.on.map((p, idx): [string, string] =>
      idx === pi ? (side === "l" ? [value, p[1]] : [p[0], value]) : p,
    );
    patchJoinAt(ji, { on });
  }
  function addJoin() {
    if (combine?.op !== "join") return;
    onCombineChange({
      ...combine,
      joins: [
        ...joins,
        { left: names[0] ?? "", right: names[1] ?? "", on: [["", ""]], how: "inner" },
      ],
    });
  }
  function removeJoin(ji: number) {
    if (combine?.op !== "join") return;
    onCombineChange({ ...combine, joins: joins.filter((_, i) => i !== ji) });
  }

  return (
    <div className="rl-sources">
      <span className="rl-hint">
        Each source is a SQL query or an uploaded file that resolves to rows. Give
        each a short name; with 2+ sources, choose how to combine them below.
      </span>
      {sources.map((src, idx) => {
        const ds = src.file_ref ? uploads[src.file_ref] : undefined;
        return (
          <div key={idx} className="rl-source-card">
            <div className="rl-source-head">
              <input
                className="rl-source-name"
                value={src.name}
                onChange={(e) => patchSource(idx, { name: e.target.value })}
                placeholder="source name"
                aria-label="Source name"
              />
              <div className="rl-actions">
                {(["sql", "file"] as const).map((t) => (
                  <button
                    type="button"
                    key={t}
                    className={src.type === t ? "rl-btn rl-btn-primary" : "rl-btn"}
                    onClick={() => patchSource(idx, { type: t })}
                  >
                    {t === "sql" ? "SQL" : "File"}
                  </button>
                ))}
                <button
                  type="button"
                  className="rl-btn"
                  onClick={() => removeSource(idx)}
                  title="Remove source"
                >
                  ✕
                </button>
              </div>
            </div>

            {src.type === "sql" ? (
              <ExpandableTextarea
                label={`Source “${src.name}” — SQL`}
                value={src.sql ?? ""}
                onChange={(v) => patchSource(idx, { sql: v })}
                placeholder={"SELECT id, region FROM policies"}
                rows={3}
                monospace
              />
            ) : (
              <div className="rl-source-file">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xlsm"
                  disabled={busyIdx === idx}
                  onChange={(e) => onPickFile(idx, e.target.files?.[0] ?? null)}
                />
                {busyIdx === idx && <span className="rl-hint">Uploading…</span>}
                {ds && (
                  <span className="rl-hint">
                    <strong>{ds.filename}</strong> — {ds.row_count} rows,{" "}
                    {Object.keys(ds.columns).length} cols (
                    {Object.keys(ds.columns).join(", ")})
                  </span>
                )}
                {!ds && src.file_ref && (
                  <span className="rl-hint">ref: {src.file_ref}</span>
                )}
              </div>
            )}
          </div>
        );
      })}

      {uploadError && <div className="rl-banner rl-banner-error">{uploadError}</div>}

      <button type="button" className="rl-btn" onClick={addSource}>
        + Add source
      </button>

      {multi && (
        <div className="rl-combine">
          <label className="rl-hint" style={{ fontWeight: 600 }}>
            Combine sources
          </label>
          <div className="rl-actions">
            {(["join", "union"] as const).map((op) => (
              <button
                type="button"
                key={op}
                className={combine?.op === op ? "rl-btn rl-btn-primary" : "rl-btn"}
                onClick={() => setOp(op)}
              >
                {op}
              </button>
            ))}
          </div>

          {combine?.op === "union" && (
            <label className="rl-hint" style={{ display: "block", marginTop: 8 }}>
              <input
                type="checkbox"
                checked={combine.distinct ?? false}
                onChange={(e) =>
                  onCombineChange({ ...combine, distinct: e.target.checked })
                }
              />{" "}
              Drop duplicate rows (distinct)
            </label>
          )}

          {combine?.op === "join" && (
            <div className="rl-joins">
              {joins.map((join, ji) => (
                <div key={ji} className="rl-join">
                  <div className="rl-join-row">
                    <select
                      value={join.left}
                      onChange={(e) => patchJoinAt(ji, { left: e.target.value })}
                      aria-label="Left source"
                    >
                      {names.map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                    <select
                      value={join.how ?? "inner"}
                      onChange={(e) =>
                        patchJoinAt(ji, { how: e.target.value as JoinInput["how"] })
                      }
                      aria-label="Join type"
                    >
                      <option value="inner">inner join</option>
                      <option value="left">left join</option>
                    </select>
                    <select
                      value={join.right}
                      onChange={(e) => patchJoinAt(ji, { right: e.target.value })}
                      aria-label="Right source"
                    >
                      {names.map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                    <button
                      type="button"
                      className="rl-btn"
                      onClick={() => removeJoin(ji)}
                      title="Remove join"
                    >
                      ✕
                    </button>
                  </div>
                  <span className="rl-hint">on key pairs (left column = right column)</span>
                  {join.on.map((pair, pi) => (
                    <div key={pi} className="rl-join-row">
                      <input
                        value={pair[0]}
                        onChange={(e) => patchPairAt(ji, pi, "l", e.target.value)}
                        placeholder={`${join.left} column`}
                      />
                      <span>=</span>
                      <input
                        value={pair[1]}
                        onChange={(e) => patchPairAt(ji, pi, "r", e.target.value)}
                        placeholder={`${join.right} column`}
                      />
                      <button
                        type="button"
                        className="rl-btn"
                        onClick={() =>
                          patchJoinAt(ji, { on: join.on.filter((_, idx) => idx !== pi) })
                        }
                        disabled={join.on.length <= 1}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                  <button
                    type="button"
                    className="rl-btn"
                    onClick={() => patchJoinAt(ji, { on: [...join.on, ["", ""]] })}
                  >
                    + Add key pair
                  </button>
                </div>
              ))}
              <button type="button" className="rl-btn" onClick={addJoin}>
                + Add join
              </button>
              <span className="rl-hint">
                Joins apply left-to-right; chain a third source by joining it onto
                a source already used above.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
