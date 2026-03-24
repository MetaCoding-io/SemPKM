---
estimated_steps: 4
estimated_files: 3
skills_used:
  - react-best-practices
---

# T02: API Client & Auth Provider

**Slice:** S03 — Mobile App Foundation & API Connection
**Milestone:** M037

## Description

Create the TypeScript API client, secure storage hook, and SessionProvider — three pure TypeScript modules with no UI. The API client mirrors the extension's `SemPKMClient` pattern. The auth provider follows the Expo docs' recommended `SessionProvider` + `useStorageState` pattern for credential management.

## Steps

1. Create `mobile/src/api/client.ts`:
   - Define TypeScript interfaces: `InstanceInfo` (version, endpoints, capabilities), `ContextResponse` (location_zone, activity, time_period, calendar_event, calendar_busy, device_id, is_stale, updated_at, ttl_seconds — all fields optional/nullable matching backend), `ContextUpdate` (location_zone?, activity?, time_period?, calendar_event?, calendar_busy?, device_id?)
   - Define `SemPKMError` class extending Error with `status: number` and `detail: string | null`
   - Define `SemPKMClient` class with `constructor(instanceUrl: string, apiKey: string)` (strip trailing slash), private `headers(): HeadersInit`, async `request<T>(path: string, options?: RequestInit): Promise<T>` (fetch + error handling), `connect(): Promise<InstanceInfo>` (GET /.well-known/sempkm), `getCurrentContext(): Promise<ContextResponse>` (GET /api/context/current), `updateContext(data: ContextUpdate): Promise<ContextResponse>` (POST /api/context/update with JSON body)
   - Mirror the extension's error handling: parse JSON detail on non-ok response, throw SemPKMError

2. Create `mobile/src/hooks/useStorageState.ts`:
   - Import `SecureStore` from `expo-secure-store` and `Platform` from `react-native`
   - Implement `useStorageState(key: string): [[boolean, string | null], (value: string | null) => void]`
   - On mount: load value from SecureStore (or localStorage on web), set loading=false
   - Setter: update React state and persist to SecureStore (or delete if null)
   - Follow the Expo docs pattern: `useReducer` for `[isLoading, value]` state, `useEffect` for initial load

3. Create `mobile/src/ctx.tsx`:
   - Define `AuthContextType` with `signIn(url: string, apiKey: string): void`, `signOut(): void`, `session: string | null`, `isLoading: boolean`
   - Create `AuthContext` via `createContext<AuthContextType>`
   - Export `useSession()` hook that reads from `AuthContext` and throws if used outside provider
   - Export `SessionProvider` component: uses `useStorageState('session')`, `signIn` serializes `{instanceUrl, apiKey}` to JSON and stores, `signOut` stores null, provides context value to children

4. Verify TypeScript compiles cleanly: `cd mobile && npx tsc --noEmit`

## Must-Haves

- [ ] `SemPKMClient` class with connect(), getCurrentContext(), updateContext() methods
- [ ] TypeScript interfaces for InstanceInfo, ContextResponse, ContextUpdate matching backend schema
- [ ] `SemPKMError` with HTTP status and parsed detail
- [ ] `useStorageState` hook using expo-secure-store
- [ ] `SessionProvider` with signIn/signOut/session/isLoading
- [ ] `useSession()` hook with context-missing guard
- [ ] Zero TypeScript errors

## Verification

- `cd mobile && npx tsc --noEmit` exits with code 0
- `grep -q "getCurrentContext" mobile/src/api/client.ts` — API client has context method
- `grep -q "SessionProvider" mobile/src/ctx.tsx` — auth provider exists
- `grep -q "SecureStore" mobile/src/hooks/useStorageState.ts` — uses secure store

## Observability Impact

- **API client errors:** `SemPKMError` carries `status` (HTTP code, or 0 for network errors) and `detail` (parsed backend message). Callers surface these to the user — never swallowed silently.
- **Auth state inspection:** Session stored in `expo-secure-store` under key `session`. A null session means unauthenticated. JSON payload shape: `{ instanceUrl, apiKey }`. Use `parseSession()` to safely decode.
- **Storage load state:** `useStorageState` returns `[isLoading, value]` — `isLoading=true` until the initial SecureStore read completes. Screens should show a loading indicator during this phase to avoid flash-of-wrong-state.
- **Context-missing guard:** `useSession()` throws an explicit error if called outside `<SessionProvider>`, providing a clear diagnostic message for wiring mistakes.

## Inputs

- `mobile/package.json` — Expo project with expo-secure-store installed (from T01)
- `mobile/tsconfig.json` — TypeScript configuration (from T01)
- `extension/shared/api-client.js` — reference pattern for API client structure (read only, not modified)

## Expected Output

- `mobile/src/api/client.ts` — SemPKM TypeScript API client
- `mobile/src/hooks/useStorageState.ts` — secure storage React hook
- `mobile/src/ctx.tsx` — SessionProvider and useSession
