import { useEffect, useRef, useState } from "react";

interface Props {
  id?: string;
  /** Shown in the expanded modal's header + button tooltip. */
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  monospace?: boolean;
  spellCheck?: boolean;
  /** When true, the modal offers a "Format JSON" action. */
  json?: boolean;
}

/** A textarea with an “expand” affordance that opens a large dedicated editor
 * modal for the same value — useful for SQL, JSON, and long descriptions. */
export function ExpandableTextarea({
  id,
  label,
  value,
  onChange,
  placeholder,
  rows = 4,
  monospace,
  spellCheck,
  json,
}: Props) {
  const [open, setOpen] = useState(false);
  const cls = `rl-exp-textarea${monospace ? " rl-mono" : ""}`;
  return (
    <div className="rl-exp">
      <textarea
        id={id}
        className={cls}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        spellCheck={spellCheck}
      />
      <button
        type="button"
        className="rl-exp-btn"
        title={`Expand — ${label}`}
        aria-label={`Expand ${label}`}
        onClick={() => setOpen(true)}
      >
        ⤢
      </button>
      {open && (
        <TextModal
          label={label}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          monospace={monospace}
          spellCheck={spellCheck}
          json={json}
          onClose={() => setOpen(false)}
        />
      )}
    </div>
  );
}

function TextModal({
  label,
  value,
  onChange,
  placeholder,
  monospace,
  spellCheck,
  json,
  onClose,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  monospace?: boolean;
  spellCheck?: boolean;
  json?: boolean;
  onClose: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [jsonError, setJsonError] = useState<string | null>(null);

  useEffect(() => {
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") onClose();
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [onClose]);

  function formatJson() {
    try {
      onChange(JSON.stringify(JSON.parse(value || "{}"), null, 2));
      setJsonError(null);
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : "Invalid JSON.");
    }
  }

  const chars = value.length;
  const lines = value ? value.split("\n").length : 0;

  return (
    <div className="rl-modal-backdrop" onMouseDown={onClose}>
      <div
        className="rl-modal"
        role="dialog"
        aria-modal="true"
        aria-label={label}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="rl-modal-head">
          <span>{label}</span>
          <div className="rl-actions">
            {json && (
              <button type="button" className="rl-btn" onClick={formatJson}>
                Format JSON
              </button>
            )}
            <button type="button" className="rl-btn rl-btn-primary" onClick={onClose}>
              Done
            </button>
          </div>
        </div>
        <textarea
          ref={ref}
          className={`rl-modal-textarea${monospace ? " rl-mono" : ""}`}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            if (jsonError) setJsonError(null);
          }}
          placeholder={placeholder}
          spellCheck={spellCheck}
        />
        {jsonError && (
          <div className="rl-banner rl-banner-error" style={{ marginTop: 8 }}>
            Invalid JSON: {jsonError}
          </div>
        )}
        <div className="rl-modal-foot">
          <span className="rl-hint">
            {chars.toLocaleString()} chars · {lines.toLocaleString()} lines
          </span>
          <span className="rl-hint">
            Edits save live. <strong>Ctrl/Cmd+Enter</strong>, <strong>Esc</strong>, or{" "}
            <strong>Done</strong> to close.
          </span>
        </div>
      </div>
    </div>
  );
}
