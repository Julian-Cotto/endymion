import { getShellAuthMode } from "../auth/msalConfig";
import { getShellSessionSnapshot } from "../session/shellSessionStore";

function normalizeCsv(values: string[] | undefined): string | undefined {
  const normalized = (values ?? [])
    .map((value) => value.trim())
    .filter(Boolean);

  if (normalized.length === 0) {
    return undefined;
  }

  return normalized.join(",");
}

export function buildRuntimeRequestHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  const session = getShellSessionSnapshot();
  const token = session?.accessToken?.trim();

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  if (getShellAuthMode() === "mock") {
    if (session?.userId) {
      headers["X-Debug-User-Id"] = session.userId;
    }

    if (session?.userName) {
      headers["X-Debug-User-Name"] = session.userName;
    }

    if (session?.email) {
      headers["X-Debug-Email"] = session.email;
    }

    const roles = normalizeCsv(session?.roles);
    if (roles) {
      headers["X-Debug-Roles"] = roles;
    }
  }

  return headers;
}