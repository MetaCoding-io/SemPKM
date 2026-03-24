---
id: T03
parent: S03
milestone: M037
provides:
  - Root layout wrapping entire app in SessionProvider
  - Authenticated route guard redirecting to /sign-in when no session
  - Sign-in onboarding screen with URL + API key inputs, connection test, error display
  - Placeholder authenticated index page (T04 replaces with full tabs)
key_files:
  - mobile/src/app/_layout.tsx
  - mobile/src/app/sign-in.tsx
  - mobile/src/app/(app)/_layout.tsx
  - mobile/src/app/(app)/index.tsx
key_decisions:
  - Removed all SDK 55 demo components (animated-icon, app-tabs, themed-text, etc.) — none referenced by app code, and app-tabs.web.tsx caused TS errors referencing the deleted /explore route
  - Removed demo routes (index.tsx, explore.tsx) from root app/ — expo-router would match them before the (app) group, breaking the auth flow
patterns_established:
  - Root _layout.tsx is pure SessionProvider + Slot — no theme or navigation chrome at this level
  - Authenticated group uses (app)/ directory with _layout.tsx as the guard gate
  - sign-in.tsx uses SemPKMClient.connect() for connection validation before storing credentials
  - Error states mapped from SemPKMError.status — 0 for network, 401 for auth, else generic
observability_surfaces:
  - "Route guard: unauthenticated → /sign-in redirect; authenticated → child slot. useSession() outside SessionProvider throws immediately."
  - "Sign-in errors: inline red text with specific messages per error type (network, auth, format, generic)"
  - "Loading state: ActivityIndicator during connection test (connecting=true) and during initial storage read (isLoading=true)"
  - "Credential redaction: API key uses secureTextEntry; never logged or displayed post-entry"
duration: 8m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T03: Onboarding Screen & Route Guards

**Created sign-in screen with connection test and error handling, route guard redirecting unauthenticated users, and cleaned up SDK 55 demo components.**

## What Happened

Replaced the SDK 55 template root layout (which used demo `AppTabs` and `AnimatedSplashOverlay` components) with a clean `SessionProvider` + `Slot` wrapper. Created `(app)/_layout.tsx` as the authenticated route guard — it checks `useSession()` state and redirects to `/sign-in` when no session exists, showing a loading indicator during the initial secure-store read.

Built the sign-in screen with two TextInputs (instance URL with URL keyboard type, API key with secureTextEntry), a Connect button that instantiates `SemPKMClient` and calls `connect()`, and inline error display. Error states are mapped specifically: status 0 → "Could not reach server", status 401 → "Invalid API key", invalid URL format → "URL must start with http:// or https://", and a generic fallback for other server errors. ActivityIndicator replaces the button text during connection. KeyboardAvoidingView handles iOS/Android keyboard overlap.

Removed the SDK 55 demo routes (`index.tsx`, `explore.tsx`) from the root `src/app/` — these would have been matched by expo-router before the `(app)` group, preventing the auth redirect flow. Also removed all demo components (`src/components/`) and orphaned hooks (`use-color-scheme`) since none were referenced by app code, and `app-tabs.web.tsx` caused a TS error referencing the deleted `/explore` route.

Created a placeholder `(app)/index.tsx` so the authenticated route has a landing page — T04 will replace this with the full tab navigator and dashboard.

Regenerated expo-router typed routes by starting Metro (the `.expo/types/router.d.ts` file now includes `/sign-in` and `/(app)` routes).

## Verification

- `npx tsc --noEmit` — zero TypeScript errors (exit 0)
- `grep -q "useSession" mobile/src/app/sign-in.tsx` — uses auth context ✅
- `grep -q "SemPKMClient" mobile/src/app/sign-in.tsx` — uses API client ✅
- `grep -q "Redirect" mobile/src/app/(app)/_layout.tsx` — route guard redirects ✅
- Core modules exist (client.ts, ctx.tsx, useStorageState.ts) ✅
- Metro bundler starts and prints "Waiting on http://localhost:8081" ✅
- Slice V4 (screen files): sign-in.tsx ✅, (tabs)/index.tsx ⏳ T04, (tabs)/settings.tsx ⏳ T04

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | ~3s |
| 2 | `grep -q "useSession" mobile/src/app/sign-in.tsx` | 0 | ✅ pass | <1s |
| 3 | `grep -q "SemPKMClient" mobile/src/app/sign-in.tsx` | 0 | ✅ pass | <1s |
| 4 | `grep -q "Redirect" mobile/src/app/(app)/_layout.tsx` | 0 | ✅ pass | <1s |
| 5 | `test -f mobile/src/api/client.ts && test -f mobile/src/ctx.tsx && test -f mobile/src/hooks/useStorageState.ts` (slice V3) | 0 | ✅ pass | <1s |
| 6 | `cd mobile && CI=1 timeout 20 npx expo start --no-dev --non-interactive` (slice V2) | 0 | ✅ pass (Metro "Waiting on http://localhost:8081") | ~20s |
| 7 | `test -f mobile/src/app/sign-in.tsx` (slice V4 partial) | 0 | ✅ pass | <1s |
| 8 | `test -f mobile/src/app/(app)/(tabs)/index.tsx` (slice V4 partial) | 1 | ⏳ expected fail (T04 deliverable) | <1s |

## Diagnostics

- `cd mobile && npx tsc --noEmit` — TypeScript health check
- `grep -c "setError" mobile/src/app/sign-in.tsx` — count error-setting paths (expect 4: URL validation, network, 401, generic)
- `grep "SemPKMError" mobile/src/app/sign-in.tsx` — verify error class usage in catch block
- Route guard observable behavior: remove session from SecureStore → app redirects to /sign-in; add session → app shows (app)/ route

## Deviations

- Removed all SDK 55 demo components (`src/components/`, `src/constants/`, orphaned hooks) — not in the task plan. The demo `app-tabs.web.tsx` referenced the deleted `/explore` route causing a TS error, and no demo component is used by any app screen.
- Removed `index.tsx` and `explore.tsx` from root `src/app/` — necessary because expo-router matches root-level routes before group routes, which would bypass the `(app)/_layout.tsx` auth guard.
- Created `(app)/index.tsx` placeholder — not in the task plan but required so the authenticated route guard's `<Slot/>` has a child to render. T04 replaces this with the full tab navigator.

## Known Issues

- Metro bundler's `--non-interactive` flag doesn't work as a CLI arg in SDK 55; `CI=1` environment variable is needed instead (same as T01).

## Files Created/Modified

- `mobile/src/app/_layout.tsx` — Root layout: SessionProvider + Slot (replaced SDK 55 template layout)
- `mobile/src/app/sign-in.tsx` — Onboarding screen with URL/API key inputs, connection test, error display
- `mobile/src/app/(app)/_layout.tsx` — Authenticated route guard: redirects to /sign-in when no session
- `mobile/src/app/(app)/index.tsx` — Placeholder index for authenticated area (T04 replaces)
- `mobile/src/app/index.tsx` — DELETED (demo route, conflicted with (app) group routing)
- `mobile/src/app/explore.tsx` — DELETED (demo route)
- `mobile/src/components/` — DELETED (all SDK 55 demo components — unused by app code)
- `mobile/src/constants/` — DELETED (SDK 55 demo constants — unused by app code)
- `mobile/src/hooks/use-color-scheme.ts` — DELETED (orphaned demo hook)
- `mobile/src/hooks/use-color-scheme.web.ts` — DELETED (orphaned demo hook)
- `.gsd/milestones/M037/slices/S03/tasks/T03-PLAN.md` — Added Observability Impact section
