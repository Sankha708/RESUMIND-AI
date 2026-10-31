"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { getApiBaseUrl } from "@/lib/api";

export interface SessionInfo {
  id: string;
  created_at: string;
  expires_at: string;
  is_active: boolean;
}

interface SessionContextType {
  session: SessionInfo | null;
  loading: boolean;
  error: string | null;
  backendOnline: boolean;
  refreshSession: () => Promise<void>;
  resetSession: () => Promise<boolean>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);

  // Guard against React Strict Mode duplicate execution
  const initializedRef = useRef<boolean>(false);

  const apiBaseUrl = getApiBaseUrl();

  const initSession = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Attempt to retrieve existing session or mint new one via cookie
      const res = await fetch(`${apiBaseUrl}/api/session`, {
        method: "POST",
        credentials: "include", // Essential for HttpOnly cookie exchange
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!res.ok) {
        throw new Error(`Session endpoint returned status ${res.status}`);
      }

      const data: SessionInfo = await res.json();
      setSession(data);
      setBackendOnline(true);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Backend unavailable";
      setError(errMsg);
      setBackendOnline(false);
      // Graceful fallback: do not crash client when backend is not running
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl]);

  const resetSession = async (): Promise<boolean> => {
    try {
      setLoading(true);
      const response = await fetch(`${apiBaseUrl}/api/session/reset`, {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error(`Session reset failed (${response.status}).`);
      }
      setSession(null);
      // Re-initialize a fresh anonymous session
      await initSession();
      return true;
    } catch (err: unknown) {
      console.warn("Failed to reset session:", err);
      setError(err instanceof Error ? err.message : "Failed to reset the active session.");
      return false;
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true;
      initSession();
    }
  }, [initSession]);

  return (
    <SessionContext.Provider
      value={{
        session,
        loading,
        error,
        backendOnline,
        refreshSession: initSession,
        resetSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextType {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useSession must be used within a SessionProvider");
  }
  return context;
}
