/**
 * Auth context provider for SemPKM mobile app.
 *
 * Manages session credentials (instance URL + API key) in secure
 * storage and exposes signIn / signOut / session / isLoading to
 * the component tree.
 *
 * The session value is a JSON string: { instanceUrl, apiKey }.
 * Null session = unauthenticated.
 *
 * @module ctx
 */

import React, { createContext, useContext, type PropsWithChildren } from 'react';

import { useStorageState } from '@/hooks/useStorageState';

// ── Types ───────────────────────────────────────────────────────

export interface SessionPayload {
  instanceUrl: string;
  apiKey: string;
}

interface AuthContextType {
  /** Sign in by persisting instance URL and API key. */
  signIn: (url: string, apiKey: string) => void;
  /** Clear stored credentials. */
  signOut: () => void;
  /**
   * Raw session string (JSON-serialized SessionPayload) or null
   * when unauthenticated.
   */
  session: string | null;
  /** True while the initial storage read is in progress. */
  isLoading: boolean;
}

// ── Context ─────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextType | null>(null);

/**
 * Read the auth context. Throws if used outside a <SessionProvider>.
 */
export function useSession(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error(
      'useSession() must be used inside a <SessionProvider>. ' +
        'Wrap your app root with <SessionProvider>.',
    );
  }
  return ctx;
}

/**
 * Parse a raw session string into a typed payload.
 * Returns null on invalid/missing session.
 */
export function parseSession(session: string | null): SessionPayload | null {
  if (!session) return null;
  try {
    const parsed = JSON.parse(session);
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      typeof parsed.instanceUrl === 'string' &&
      typeof parsed.apiKey === 'string'
    ) {
      return parsed as SessionPayload;
    }
    return null;
  } catch {
    return null;
  }
}

// ── Provider ────────────────────────────────────────────────────

/**
 * Provides auth state to the entire component tree.
 *
 * Reads/writes the "session" key in expo-secure-store via the
 * useStorageState hook. The stored value is a JSON string:
 *   { "instanceUrl": "https://...", "apiKey": "sk-..." }
 *
 * signIn() serialises the credentials and stores them.
 * signOut() clears the stored value (sets null).
 */
export function SessionProvider({ children }: PropsWithChildren) {
  const [[isLoading, session], setSession] = useStorageState('session');

  const signIn = (url: string, apiKey: string) => {
    const payload: SessionPayload = {
      instanceUrl: url.replace(/\/+$/, ''),
      apiKey,
    };
    setSession(JSON.stringify(payload));
  };

  const signOut = () => {
    setSession(null);
  };

  return (
    <AuthContext.Provider value={{ signIn, signOut, session, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}
