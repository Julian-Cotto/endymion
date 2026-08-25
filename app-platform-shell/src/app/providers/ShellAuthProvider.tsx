import { createContext, useContext, useMemo, type ReactNode } from "react";

import type { ShellUserSession } from "../../platform/auth/sessionTypes";

const ShellAuthContext = createContext<ShellUserSession | undefined>(undefined);

export interface ShellAuthProviderProps {
  session: ShellUserSession;
  children: ReactNode;
}

export function ShellAuthProvider({ session, children }: ShellAuthProviderProps) {
  const value = useMemo(() => session, [session]);

  return <ShellAuthContext.Provider value={value}>{children}</ShellAuthContext.Provider>;
}

export function useShellSession(): ShellUserSession {
  const context = useContext(ShellAuthContext);

  if (!context) {
    throw new Error("useShellSession must be used inside ShellAuthProvider.");
  }

  return context;
}