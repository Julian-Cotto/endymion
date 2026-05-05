import { Html5Qrcode } from "html5-qrcode";
import { useEffect, useRef, useState } from "react";

import CameraScanner from "./CameraScanner";
import { SCANNER_CONFIG } from "./scanFormats";

interface Props {
  value: string;
  onChange: (value: string) => void;
  onScan?: (value: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  label?: string;
}

export default function ScanInput({
  value,
  onChange,
  onScan,
  placeholder = "Scan or type serial",
  autoFocus = true,
  label = "Serial number",
}: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [showCamera, setShowCamera] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  useEffect(() => {
    if (autoFocus) inputRef.current?.focus();
  }, [autoFocus]);

  const accept = (text: string) => {
    onChange(text);
    onScan?.(text);
  };

  const handleUpload = async (file: File) => {
    setFileError(null);
    try {
      const inst = new Html5Qrcode(
        "__hidden_scan_target__",
        SCANNER_CONFIG as never,
      );
      const decoded = await inst.scanFile(file, false);
      accept(decoded);
    } catch (err) {
      setFileError(
        err instanceof Error
          ? err.message
          : "Could not decode a code from that image",
      );
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  return (
    <div>
      <label style={{ display: "block", fontSize: 12, marginBottom: 4 }}>
        {label}
      </label>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && onScan && value.trim()) {
              e.preventDefault();
              onScan(value.trim());
            }
          }}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          style={{ flex: "1 1 220px", padding: "6px 8px", fontFamily: "monospace" }}
        />
        <button type="button" onClick={() => setShowCamera(true)}>
          Camera
        </button>
        <button type="button" onClick={() => fileRef.current?.click()}>
          Upload image
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handleUpload(f);
          }}
        />
      </div>
      {fileError && (
        <div style={{ fontSize: 12, color: "crimson", marginTop: 4 }}>
          {fileError}
        </div>
      )}
      {/* hidden mount target for Html5Qrcode.scanFile */}
      <div id="__hidden_scan_target__" style={{ display: "none" }} />
      {showCamera && (
        <CameraScanner
          onResult={(text) => {
            setShowCamera(false);
            accept(text);
          }}
          onClose={() => setShowCamera(false)}
        />
      )}
    </div>
  );
}
