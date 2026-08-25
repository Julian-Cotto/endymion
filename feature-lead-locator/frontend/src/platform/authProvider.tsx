import { createContext, useContext, type ReactNode } from "react";

import { resolveFeatureAuthContext } from "./authAdapter";

const AuthContext = createContext<any>(undefined);

export function FeatureAuthProvider({ children }: { children: ReactNode }) {
  const value = resolveFeatureAuthContext();

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useFeatureAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useFeatureAuth must be used inside FeatureAuthProvider.");
  }

  return context;
}