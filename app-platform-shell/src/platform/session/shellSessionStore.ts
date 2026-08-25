import type { ShellUserSession } from "../auth/sessionTypes";

let currentSession: ShellUserSession | null = null;

export function setShellSessionSnapshot(
  session: ShellUserSession | null,
): void {
  currentSession = session;
}

export function getShellSessionSnapshot(): ShellUserSession | null {
  return currentSession;
}

export function clearShellSessionSnapshot(): void {
  currentSession = null;
}