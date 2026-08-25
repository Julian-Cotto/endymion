export interface ShellUserSession {
    isAuthenticated: boolean;
    userId?: string;
    userName?: string;
    email?: string;
    roles?: string[];
    accessToken?: string;
  }