import { useEffect, useState } from "react";
import { getHealth } from "../services/featureApi";
import type { ShellMountContext } from "../platform/shellContext";

type HealthResponse = {
  status: string;
  service: string;
  feature_key: string;
  auth_mode: string;
};

export function BackendHealthCard({
  shellContext,
}: {
  shellContext?: ShellMountContext;
}) {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth(shellContext)
      .then(setHealth)
      .catch((err: Error) => setError(err.message));
  }, [shellContext]);

  return (
    <section style={{ border: "1px solid #ccc", padding: "12px", marginTop: "16px" }}>
      <h2>Backend health</h2>
      {!health && !error && <p>Loading health...</p>}
      {error && <p>Health check failed: {error}</p>}
      {health && (
        <div>
          <p>Status: <strong>{health.status}</strong></p>
          <p>Auth mode: <strong>{health.auth_mode}</strong></p>
        </div>
      )}
    </section>
  );
}