import { useEffect, useState } from "react";

import { useFeatureAuth } from "./platform/authProvider";
import { apiFetch } from "./services/apiClient";

const FEATURE_NAME = "Lead Locator";

type FeatureItem = {
  id: string;
  name: string;
  status: string;
};

type FeatureItemsResponse = {
  feature_key?: string;
  authenticated?: boolean;
  user?: string;
  items?: FeatureItem[];
};

export default function App() {
  const auth = useFeatureAuth();
  const [data, setData] = useState<FeatureItemsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        const json = await apiFetch<FeatureItemsResponse>("/items");

        if (isMounted) {
          setData(json);
          setError(null);
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setData(null);
        }
      }
    }

    void load();

    return () => {
      isMounted = false;
    };
  }, []);

  if (!auth.isAuthenticated && auth.authMode === "entra") {
    return (
      <div>
        <h1>{FEATURE_NAME}</h1>
        <p>This feature requires shell authentication.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1>{FEATURE_NAME}</h1>
        <p>{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div>
        <h1>{FEATURE_NAME}</h1>
        <p>Loading...</p>
      </div>
    );
  }

  const items = Array.isArray(data.items) ? data.items : [];

  const displayUser =
    auth.userName ||
    auth.email ||
    data.user ||
    "unknown user";

  return (
    <div>
      <h1>{FEATURE_NAME}</h1>
      <p>Signed in as: {displayUser}</p>

      {items.length === 0 ? (
        <p>No items returned.</p>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <strong>{item.name}</strong> — {item.status}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}