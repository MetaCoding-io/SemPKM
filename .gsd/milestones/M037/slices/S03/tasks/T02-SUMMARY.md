---
id: T02
parent: S03
milestone: M037
provides:
  - SemPKMClient TypeScript API client with connect(), getCurrentContext(), updateContext()
  - TypeScript interfaces for InstanceInfo, ContextResponse, ContextUpdate matching backend
  - SemPKMError class with HTTP status and parsed detail
  - useStorageState hook wrapping expo-secure-store with React state sync
  - SessionProvider with signIn/signOut/session/isLoading context
  - useSession() hook with context-missing guard
  - parseSession() utility for safe JSON decoding
key_files:
  - mobile/src/api/client.ts
  - mobile/src/hooks/useStorageState.ts
  - mobile/src/ctx.tsx
key_decisions:
  - Network errors get status 0 in SemPKMError (distinguishes offline from server errors)
  - parseSession() exported as a standalone utility so screens can decode session without duplicating JSON.parse
  - useStorageState uses Platform.OS check to fall back to localStorage on web (mirrors Expo docs pattern)
patterns_established:
  - SemPKMClient follows same constructor/headers/request/connect pattern as extension api-client.js
  - Session payload is JSON { instanceUrl, apiKey } stored under SecureStore key "session"
  - useReducer + useEffect for async storage load avoids stale-closure issues vs useState
observability_surfaces:
  - "SemPKMError.status — 0 for network errors, HTTP code for server errors"
  - "SemPKMError.detail — parsed backend detail string or statusText"
  - "useSession() throws if called outside <SessionProvider> — immediate diagnostic for wiring errors"
  - "useStorageState returns [isLoading, value] — loading=true until SecureStore read completes"
duration: 8m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: API Client & Auth Provider

**Created TypeScript API client, secure storage hook, and SessionProvider — three pure modules with full type coverage matching the backend context API.**

## What Happened

Created `mobile/src/api/client.ts` mirroring the extension's `SemPKMClient` pattern but with full TypeScript types. The `InstanceInfo`, `ContextResponse`, and `ContextUpdate` interfaces match the backend Pydantic models exactly (verified by reading `backend/app/api/router.py` for InstanceInfo and `backend/app/context/service.py` for ContextData fields). The `request()` method wraps network errors in `SemPKMError` with status 0, distinguishing them from server errors — this is important for the sign-in screen's error display.

Created `mobile/src/hooks/useStorageState.ts` following the Expo docs pattern: `useReducer` for `[isLoading, value]` state, `useEffect` for initial async load from SecureStore, `useCallback` for the setter. Falls back to `localStorage` on web via `Platform.OS` check.

Created `mobile/src/ctx.tsx` with `SessionProvider` that uses `useStorageState('session')` and serialises credentials as `JSON.stringify({ instanceUrl, apiKey })`. Exported `parseSession()` as a utility for downstream screens to decode the session without repeating JSON.parse logic. `useSession()` throws an explicit error if used outside the provider.

## Verification

- `npx tsc --noEmit` — zero TypeScript errors
- `grep -q "getCurrentContext" mobile/src/api/client.ts` — API client has context method
- `grep -q "SessionProvider" mobile/src/ctx.tsx` — auth provider exists
- `grep -q "SecureStore" mobile/src/hooks/useStorageState.ts` — uses secure store
- Slice check: core modules exist (client.ts, ctx.tsx, useStorageState.ts)
- Slice check: screen files don't exist yet — expected, those are T03/T04

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | ~3s |
| 2 | `grep -q "getCurrentContext" mobile/src/api/client.ts` | 0 | ✅ pass | <1s |
| 3 | `grep -q "SessionProvider" mobile/src/ctx.tsx` | 0 | ✅ pass | <1s |
| 4 | `grep -q "SecureStore" mobile/src/hooks/useStorageState.ts` | 0 | ✅ pass | <1s |
| 5 | `test -f mobile/src/api/client.ts && test -f mobile/src/ctx.tsx && test -f mobile/src/hooks/useStorageState.ts` (slice) | 0 | ✅ pass | <1s |
| 6 | `test -f mobile/src/app/sign-in.tsx && ...` (slice — screens) | 1 | ⏳ expected fail (T03/T04) | <1s |

## Diagnostics

- `cd mobile && npx tsc --noEmit` — confirms all three modules compile cleanly
- `grep -c "async.*Promise" mobile/src/api/client.ts` — count async methods (expect 3: connect, getCurrentContext, updateContext)
- `grep "SemPKMError" mobile/src/api/client.ts | wc -l` — verify error class usage
- SemPKMError.status === 0 means network error; any other value is the HTTP status code

## Deviations

- Added `parseSession()` export to `ctx.tsx` — not in the task plan but needed by T03/T04 screens to decode the session JSON into typed `{ instanceUrl, apiKey }` without duplicating parsing logic.
- Added Observability Impact section to T02-PLAN.md as required by pre-flight check.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/api/client.ts` — SemPKM TypeScript API client with InstanceInfo, ContextResponse, ContextUpdate interfaces and SemPKMError class
- `mobile/src/hooks/useStorageState.ts` — React hook wrapping expo-secure-store with useReducer state management and web fallback
- `mobile/src/ctx.tsx` — SessionProvider context, useSession hook, and parseSession utility
- `.gsd/milestones/M037/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section
