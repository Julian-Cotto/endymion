import { Html5Qrcode } from "html5-qrcode";
import { useCallback, useEffect, useRef, useState } from "react";

import { SCANNER_CONFIG } from "./scanFormats";

interface Props {
  onResult: (text: string) => void;
  onClose: () => void;
}

const TARGET_ID = "asset-camera-scanner";

const NATIVE_FORMATS = [
  "qr_code",
  "code_128",
  "code_39",
  "code_93",
  "codabar",
  "ean_13",
  "ean_8",
  "upc_a",
  "upc_e",
  "itf",
  "data_matrix",
  "aztec",
  "pdf417",
];

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}
interface DetectedCode {
  rawValue: string;
  format?: string;
  boundingBox?: BoundingBox;
}

declare global {
  interface Window {
    BarcodeDetector?: new (opts?: { formats: string[] }) => {
      detect: (
        src: HTMLVideoElement | ImageBitmap | Blob,
      ) => Promise<DetectedCode[]>;
    };
  }
}

interface NormZone {
  x: number;
  y: number;
  w: number;
  h: number;
}

const MIN_ZONE = 0.05;
const MAX_ZONE = 1;

function clampZone(z: NormZone): NormZone {
  const w = Math.max(MIN_ZONE, Math.min(MAX_ZONE, z.w));
  const h = Math.max(MIN_ZONE, Math.min(MAX_ZONE, z.h));
  const x = Math.max(0, Math.min(1 - w, z.x));
  const y = Math.max(0, Math.min(1 - h, z.y));
  return { x, y, w, h };
}

export default function CameraScanner({ onResult, onClose }: Props) {
  const onResultRef = useRef(onResult);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const pausedRef = useRef(false);

  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("Initializing camera…");
  const [tip, setTip] = useState<string>("Point camera at the code");
  const [tipTone, setTipTone] = useState<"info" | "warn" | "good">("info");
  const [native, setNative] = useState(false);

  // Scan zone in normalized [0..1] coordinates of the displayed video.
  const [zone, setZone] = useState<NormZone>({
    x: 0.1,
    y: 0.35,
    w: 0.8,
    h: 0.3,
  });
  const zoneRef = useRef(zone);
  useEffect(() => {
    zoneRef.current = zone;
  }, [zone]);

  // Multi-candidate selection. When more than one code is in the scan zone,
  // detection pauses and these are shown as tappable boxes.
  const [candidates, setCandidates] = useState<DetectedCode[] | null>(null);

  const handleSelect = useCallback((rawValue: string) => {
    onResultRef.current(rawValue);
  }, []);

  const handleResume = useCallback(() => {
    pausedRef.current = false;
    setCandidates(null);
    void videoRef.current?.play().catch(() => {});
  }, []);

  useEffect(() => {
    const ctx: {
      cancelled: boolean;
      stream: MediaStream | null;
      video: HTMLVideoElement | null;
      rafId: number;
      h5qrInst: Html5Qrcode | null;
    } = {
      cancelled: false,
      stream: null,
      video: null,
      rafId: 0,
      h5qrInst: null,
    };

    const releaseStream = (s: MediaStream | null) => {
      s?.getTracks().forEach((t) => t.stop());
    };

    const startNative = async () => {
      setStatus("Requesting camera…");
      const acquired = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      if (ctx.cancelled) {
        releaseStream(acquired);
        return;
      }
      ctx.stream = acquired;

      const v = document.createElement("video");
      v.setAttribute("playsinline", "");
      v.muted = true;
      v.srcObject = acquired;
      v.style.width = "100%";
      v.style.borderRadius = "4px";
      v.style.display = "block";
      containerRef.current?.appendChild(v);
      try {
        await v.play();
      } catch {
        /* iOS sometimes throws on autoplay; video still renders */
      }
      if (ctx.cancelled) {
        v.parentElement?.removeChild(v);
        releaseStream(acquired);
        ctx.stream = null;
        return;
      }
      ctx.video = v;
      videoRef.current = v;

      const detector = new window.BarcodeDetector!({ formats: NATIVE_FORMATS });
      setStatus("");
      setNative(true);

      const sampleCanvas = document.createElement("canvas");
      sampleCanvas.width = 64;
      sampleCanvas.height = 36;
      const sampleCtx = sampleCanvas.getContext("2d", {
        willReadFrequently: true,
      });

      const startTime = performance.now();
      let lastFrame: Uint8ClampedArray | null = null;
      let lastTipUpdate = 0;

      const computeFrameStats = () => {
        if (!sampleCtx || !ctx.video) {
          return { motion: 0, mean: 128, contrast: 64 };
        }
        try {
          sampleCtx.drawImage(
            ctx.video,
            0,
            0,
            sampleCanvas.width,
            sampleCanvas.height,
          );
          const data = sampleCtx.getImageData(
            0,
            0,
            sampleCanvas.width,
            sampleCanvas.height,
          ).data;
          let sum = 0;
          let sumSq = 0;
          let motion = 0;
          const n = data.length / 4;
          if (!lastFrame || lastFrame.length !== n) {
            lastFrame = new Uint8ClampedArray(n);
          }
          for (let i = 0, p = 0; i < data.length; i += 4, p++) {
            const lum =
              0.2126 * data[i] + 0.7152 * data[i + 1] + 0.0722 * data[i + 2];
            sum += lum;
            sumSq += lum * lum;
            motion += Math.abs(lum - lastFrame[p]);
            lastFrame[p] = lum;
          }
          const mean = sum / n;
          const variance = Math.max(0, sumSq / n - mean * mean);
          return { motion: motion / n, mean, contrast: Math.sqrt(variance) };
        } catch {
          return { motion: 0, mean: 128, contrast: 64 };
        }
      };

      const updateTip = (
        elapsedMs: number,
        stats: { motion: number; mean: number; contrast: number },
      ) => {
        const now = performance.now();
        if (now - lastTipUpdate < 350) return;
        lastTipUpdate = now;
        if (stats.mean < 35) {
          setTipTone("warn");
          setTip("Too dark — turn on more light");
          return;
        }
        if (stats.mean > 230) {
          setTipTone("warn");
          setTip("Too bright — reduce glare on the code");
          return;
        }
        if (stats.contrast < 18) {
          setTipTone("warn");
          setTip("Low contrast — fill scan box with the code");
          return;
        }
        if (stats.motion > 18) {
          setTipTone("warn");
          setTip("Hold still — moving too fast");
          return;
        }
        if (elapsedMs > 6000) {
          setTipTone("warn");
          setTip("Not detecting. Resize the box, fill with code, ~6–10 in away");
          return;
        }
        if (elapsedMs > 2500) {
          setTipTone("info");
          setTip("Looking for code — square it inside the box");
          return;
        }
        setTipTone("info");
        setTip("Point camera at the code");
      };

      const tick = async () => {
        if (ctx.cancelled || !ctx.video) return;
        if (pausedRef.current) {
          ctx.rafId = requestAnimationFrame(tick);
          return;
        }
        const elapsed = performance.now() - startTime;
        try {
          const codes = await detector.detect(ctx.video);
          if (codes.length > 0 && ctx.video) {
            const vw = ctx.video.videoWidth;
            const vh = ctx.video.videoHeight;
            const z = zoneRef.current;
            // Filter codes whose center falls inside the scan zone.
            const inZone = codes.filter((c) => {
              if (!c.boundingBox || !vw || !vh) return true;
              const cx = (c.boundingBox.x + c.boundingBox.width / 2) / vw;
              const cy = (c.boundingBox.y + c.boundingBox.height / 2) / vh;
              return (
                cx >= z.x &&
                cx <= z.x + z.w &&
                cy >= z.y &&
                cy <= z.y + z.h
              );
            });
            if (inZone.length === 1) {
              setTipTone("good");
              setTip(`Detected: ${inZone[0].rawValue}`);
              setTimeout(() => onResultRef.current(inZone[0].rawValue), 120);
              return;
            }
            if (inZone.length > 1) {
              pausedRef.current = true;
              ctx.video.pause();
              setTipTone("info");
              setTip(
                `${inZone.length} codes in box — tap the one you want, or resize the box`,
              );
              setCandidates(inZone);
              ctx.rafId = requestAnimationFrame(tick);
              return;
            }
          }
        } catch {
          /* per-frame errors ignored */
        }
        const stats = computeFrameStats();
        updateTip(elapsed, stats);
        ctx.rafId = requestAnimationFrame(tick);
      };
      ctx.rafId = requestAnimationFrame(tick);
    };

    const startFallback = async () => {
      setStatus("Requesting camera permission…");
      const inst = new Html5Qrcode(TARGET_ID, SCANNER_CONFIG as never);
      ctx.h5qrInst = inst;
      const startConfig = { fps: 15, qrbox: { width: 280, height: 120 } };
      const decode = (text: string) => {
        setTipTone("good");
        setTip(`Detected: ${text}`);
        setTimeout(() => onResultRef.current(text), 120);
      };
      const tryStart = (src: { facingMode: string } | string) =>
        inst.start(src, startConfig, decode, () => {});
      try {
        await tryStart({ facingMode: "environment" });
      } catch {
        try {
          await tryStart({ facingMode: "user" });
        } catch {
          const cams = await Html5Qrcode.getCameras();
          if (!cams?.length) throw new Error("No camera devices.");
          await tryStart(cams[0].id);
        }
      }
      if (ctx.cancelled) {
        try {
          await inst.stop();
          inst.clear();
        } catch {
          /* noop */
        }
        ctx.h5qrInst = null;
        return;
      }
      setStatus("");
      setTipTone("info");
      setTip("Hold barcode horizontally inside the green box");
    };

    (async () => {
      try {
        if (!window.isSecureContext) {
          throw new Error("Page must be HTTPS for camera access.");
        }
        if (!navigator.mediaDevices?.getUserMedia) {
          throw new Error("getUserMedia not supported by this browser.");
        }
        if (typeof window.BarcodeDetector === "function") {
          await startNative();
        } else {
          await startFallback();
        }
      } catch (err) {
        if (!ctx.cancelled) {
          setError(err instanceof Error ? err.message : String(err));
        }
      }
    })();

    return () => {
      ctx.cancelled = true;
      cancelAnimationFrame(ctx.rafId);
      releaseStream(ctx.stream);
      ctx.stream = null;
      if (ctx.video?.parentElement) {
        ctx.video.parentElement.removeChild(ctx.video);
      }
      ctx.video = null;
      videoRef.current = null;
      if (ctx.h5qrInst) {
        const inst = ctx.h5qrInst;
        ctx.h5qrInst = null;
        void (async () => {
          try {
            await inst.stop();
            inst.clear();
          } catch {
            /* noop */
          }
        })();
      }
    };
  }, []);

  const tipColor =
    tipTone === "good" ? "#0a7" : tipTone === "warn" ? "#e80" : "#06c";

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.78)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          background: "#fff",
          padding: 16,
          borderRadius: 8,
          width: 420,
          maxWidth: "94vw",
        }}
      >
        <h3 style={{ marginTop: 0 }}>Scan barcode / QR</h3>
        <div style={{ position: "relative", width: "100%", minHeight: 250 }}>
          <div
            ref={containerRef}
            id={TARGET_ID}
            style={{ width: "100%", minHeight: 250 }}
          />
          {native && !error && !candidates && (
            <ScanZoneOverlay
              tone={tipTone}
              zone={zone}
              onChange={(z) => setZone(clampZone(z))}
            />
          )}
          {native && !error && candidates && videoRef.current && (
            <CandidateOverlay
              codes={candidates}
              video={videoRef.current}
              tone={tipTone}
              onPick={handleSelect}
            />
          )}
        </div>

        {status && !error && (
          <p style={{ fontSize: 12, color: "#666", margin: "8px 0 0" }}>
            {status}
          </p>
        )}
        {!status && !error && (
          <p
            style={{
              fontSize: 13,
              color: tipColor,
              margin: "8px 0 0",
              fontWeight: 500,
              minHeight: 18,
            }}
          >
            {tip}
          </p>
        )}
        <p style={{ fontSize: 11, color: "#888", margin: "4px 0 0" }}>
          Drag corners to resize the scan box. Pinch zooms with the OS camera if
          supported.
        </p>
        {error && (
          <p style={{ fontSize: 12, color: "crimson", margin: "8px 0 0" }}>
            {error}
          </p>
        )}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 8,
            gap: 8,
          }}
        >
          {candidates ? (
            <button onClick={handleResume}>Resume scanning</button>
          ) : (
            <span />
          )}
          <button onClick={() => onCloseRef.current()}>Close</button>
        </div>
      </div>
    </div>
  );
}

// ============================ Scan zone overlay ============================

interface OverlayProps {
  tone: "info" | "warn" | "good";
  zone: NormZone;
  onChange: (z: NormZone) => void;
}

function ScanZoneOverlay({ tone, zone, onChange }: OverlayProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const stroke =
    tone === "good" ? "#0a7" : tone === "warn" ? "#e80" : "#fc0";

  const startDrag = (
    e: React.PointerEvent<HTMLDivElement>,
    mode: "move" | "nw" | "ne" | "sw" | "se",
  ) => {
    e.preventDefault();
    e.stopPropagation();
    const wrap = wrapRef.current;
    if (!wrap) return;
    const rect = wrap.getBoundingClientRect();
    const startX = e.clientX;
    const startY = e.clientY;
    const startZone = { ...zone };
    (e.target as Element).setPointerCapture?.(e.pointerId);

    const onMove = (ev: PointerEvent) => {
      const dxN = (ev.clientX - startX) / rect.width;
      const dyN = (ev.clientY - startY) / rect.height;
      let next = { ...startZone };
      if (mode === "move") {
        next.x = startZone.x + dxN;
        next.y = startZone.y + dyN;
      } else if (mode === "nw") {
        next.x = startZone.x + dxN;
        next.y = startZone.y + dyN;
        next.w = startZone.w - dxN;
        next.h = startZone.h - dyN;
      } else if (mode === "ne") {
        next.y = startZone.y + dyN;
        next.w = startZone.w + dxN;
        next.h = startZone.h - dyN;
      } else if (mode === "sw") {
        next.x = startZone.x + dxN;
        next.w = startZone.w - dxN;
        next.h = startZone.h + dyN;
      } else if (mode === "se") {
        next.w = startZone.w + dxN;
        next.h = startZone.h + dyN;
      }
      onChange(next);
    };
    const onUp = () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    window.addEventListener("pointercancel", onUp);
  };

  const boxStyle: React.CSSProperties = {
    position: "absolute",
    left: `${zone.x * 100}%`,
    top: `${zone.y * 100}%`,
    width: `${zone.w * 100}%`,
    height: `${zone.h * 100}%`,
    boxSizing: "border-box",
    border: `2px solid ${stroke}`,
    borderRadius: 6,
    boxShadow: "0 0 0 9999px rgba(0,0,0,0.35)",
    touchAction: "none",
    cursor: "move",
  };

  const handle = (corner: "nw" | "ne" | "sw" | "se"): React.CSSProperties => ({
    position: "absolute",
    width: 28,
    height: 28,
    background: stroke,
    borderRadius: 4,
    opacity: 0.85,
    touchAction: "none",
    ...(corner === "nw" && { left: -14, top: -14, cursor: "nwse-resize" }),
    ...(corner === "ne" && { right: -14, top: -14, cursor: "nesw-resize" }),
    ...(corner === "sw" && { left: -14, bottom: -14, cursor: "nesw-resize" }),
    ...(corner === "se" && { right: -14, bottom: -14, cursor: "nwse-resize" }),
  });

  return (
    <div
      ref={wrapRef}
      style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
    >
      <div
        style={{ ...boxStyle, pointerEvents: "auto" }}
        onPointerDown={(e) => startDrag(e, "move")}
      >
        <div
          style={handle("nw")}
          onPointerDown={(e) => startDrag(e, "nw")}
        />
        <div
          style={handle("ne")}
          onPointerDown={(e) => startDrag(e, "ne")}
        />
        <div
          style={handle("sw")}
          onPointerDown={(e) => startDrag(e, "sw")}
        />
        <div
          style={handle("se")}
          onPointerDown={(e) => startDrag(e, "se")}
        />
      </div>
    </div>
  );
}

// ========================== Candidate selection ==========================

interface CandidateProps {
  codes: DetectedCode[];
  video: HTMLVideoElement;
  tone: "info" | "warn" | "good";
  onPick: (rawValue: string) => void;
}

function CandidateOverlay({ codes, video, onPick }: CandidateProps) {
  const vw = video.videoWidth || 1;
  const vh = video.videoHeight || 1;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
      }}
    >
      {codes.map((c, i) => {
        const bb = c.boundingBox;
        if (!bb) return null;
        const left = (bb.x / vw) * 100;
        const top = (bb.y / vh) * 100;
        const width = (bb.width / vw) * 100;
        const height = (bb.height / vh) * 100;
        return (
          <button
            key={`${c.rawValue}-${i}`}
            onClick={() => onPick(c.rawValue)}
            style={{
              position: "absolute",
              left: `${left}%`,
              top: `${top}%`,
              width: `${width}%`,
              height: `${height}%`,
              border: "3px solid #06c",
              background: "rgba(0,102,204,0.18)",
              borderRadius: 4,
              cursor: "pointer",
              padding: 0,
              pointerEvents: "auto",
              color: "#fff",
              fontSize: 11,
              fontFamily: "monospace",
              display: "flex",
              alignItems: "flex-end",
              justifyContent: "center",
              textShadow: "0 1px 2px rgba(0,0,0,0.8)",
            }}
            title={c.rawValue}
          >
            <span
              style={{
                background: "rgba(0,0,0,0.65)",
                padding: "2px 4px",
                borderRadius: 3,
                whiteSpace: "nowrap",
                maxWidth: "95%",
                overflow: "hidden",
                textOverflow: "ellipsis",
                margin: 2,
              }}
            >
              {c.rawValue}
            </span>
          </button>
        );
      })}
    </div>
  );
}
