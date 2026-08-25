import type { ShellUserSession } from "../../platform/auth/sessionTypes";

export function getInitials(session: ShellUserSession): string {
  const source = session.userName ?? session.email ?? session.userId ?? "?";
  const parts = source
    .replace(/@.*$/, "")
    .split(/[.\s_-]+/)
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length === 0) return "?";
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}
