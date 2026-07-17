import { useEffect, useState } from "react";
import { BackendHealthCard } from "./BackendHealthCard";
import {
  getFeatureItems,
  type FeatureItemsResponse,
} from "../services/featureApi";
import type { ShellMountContext } from "../platform/shellContext";

export function FeatureHomePage({
  shellContext,
}: {
  shellContext?: ShellMountContext;
}) {
  const [data, setData] = useState<FeatureItemsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFeatureItems(shellContext)
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, [shellContext]);

  return (
    <div style={{ fontFamily: "Arial, sans-serif", padding: "16px" }}>
      <h1>Reports Layering</h1>
      <p>Feature key: <strong>reports-layering</strong></p>
      <p>
        Authenticated:{" "}
        <strong>
          {shellContext?.session?.isAuthenticated ? "yes" : "no"}
        </strong>
      </p>
      <BackendHealthCard shellContext={shellContext} />
      <section style={{ marginTop: "20px" }}>
        <h2>Sample data</h2>
        {!data && !error && <p>Loading feature data...</p>}
        {error && <p>Failed to load feature data: {error}</p>}
        {data && (
          <ul>
            {data.items.map((item) => (
              <li key={item.id}>
                {item.name} — {item.status}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}