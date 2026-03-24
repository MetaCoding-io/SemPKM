# S03: Mobile App Foundation & API Connection

**Goal:** Create an Expo/React Native mobile app that connects to a SemPKM instance via API key and displays the current user context.
**Demo:** User installs the Expo dev build, enters their SemPKM URL and API key on the onboarding screen, sees their current context state on the dashboard, navigates between tabs (Dashboard, Zones, Settings), and can sign out and sign back in.

## Must-Haves

- Expo SDK 55 project in `mobile/` with TypeScript and expo-router
- API client (`client.ts`) mirroring the extension's `SemPKMClient` pattern with `connect()`, `getCurrentContext()`, `updateContext()` methods
- Secure credential storage via `expo-secure-store`
- Onboarding screen: instance URL + API key input, connection test, error display
- Auth route guard: unauthenticated → sign-in screen, authenticated → main app
- Dashboard screen: displays current context from `GET /api/context/current` with pull-to-refresh
- Tab navigation: Dashboard, Zones (placeholder), Settings
- Settings screen: connected instance URL, sign-out button
- `.gitignore` entries for mobile artifacts (`.expo/`, `android/`, `ios/`, etc.)
- Zero TypeScript errors (`npx tsc --noEmit`)
- Metro bundler starts without errors (`npx expo start`)

## Proof Level

- This slice proves: contract (app compiles, builds, and connects to backend API)
- Real runtime required: yes (Metro bundler must start; API client must be structurally correct)
- Human/UAT required: yes (final verification on a simulator/device is manual)

## Verification

- `cd mobile && npx tsc --noEmit` — zero TypeScript errors
- `cd mobile && npx expo start --no-dev --non-interactive 2>&1 | head -20` — Metro bundler starts (look for "Metro waiting on" or similar ready message)
- `test -f mobile/src/api/client.ts && test -f mobile/src/ctx.tsx && test -f mobile/src/hooks/useStorageState.ts` — core modules exist
- `test -f mobile/src/app/sign-in.tsx && test -f mobile/src/app/(app)/(tabs)/index.tsx && test -f mobile/src/app/(app)/(tabs)/settings.tsx` — all screens exist

## Integration Closure

- Upstream surfaces consumed: `GET /.well-known/sempkm` (connection test, S01), `GET /api/context/current` (context display, S01), `POST /api/context/update` (context push, S01) — all via Bearer token auth
- New wiring introduced in this slice: `mobile/` standalone Expo project with API client configured for Bearer auth
- What remains before the milestone is truly usable end-to-end: S04 (geofencing), S05 (calendar/activity), S06 (push notifications), S07 (integration)

## Tasks

- [ ] **T01: Expo Project Scaffold & Build Verification** `est:45m`
  - Why: The build toolchain is the highest-risk unknown — if create-expo-app or Metro bundler doesn't work, nothing else in S03-S07 can proceed. This task retires the React Native build chain risk.
  - Files: `mobile/app.json`, `mobile/package.json`, `mobile/tsconfig.json`, `.gitignore`
  - Do: Run `npx create-expo-app@latest mobile --template default@sdk-55` to scaffold the Expo project. Configure `app.json` (name: "SemPKM", slug: "sempkm", scheme: "sempkm", bundleIdentifier: "app.sempkm.mobile", package: "app.sempkm.mobile"). Install `expo-secure-store` via `npx expo install expo-secure-store`. Add mobile-specific entries to the root `.gitignore` (`mobile/.expo/`, `mobile/node_modules/`, `mobile/android/`, `mobile/ios/`, `mobile/dist/`). Verify Metro bundler starts.
  - Verify: `cd mobile && npx tsc --noEmit` exits 0; `cd mobile && npx expo start --no-dev --non-interactive` produces "Metro waiting on" within 15s
  - Done when: Expo project exists in `mobile/`, TypeScript compiles, Metro bundler starts without errors

- [ ] **T02: API Client & Auth Provider** `est:30m`
  - Why: The API client and auth state management are pure TypeScript modules with no UI — isolating them makes T03/T04 simpler and easier to test. The client mirrors the proven extension `SemPKMClient` pattern.
  - Files: `mobile/src/api/client.ts`, `mobile/src/hooks/useStorageState.ts`, `mobile/src/ctx.tsx`
  - Do: Create `client.ts` as a TypeScript class with constructor(instanceUrl, apiKey), private headers(), async request<T>(path, options), connect(), getCurrentContext(), updateContext(). Define TypeScript interfaces for InstanceInfo, ContextResponse, ContextUpdate matching the backend Pydantic models. Create custom SemPKMError class. Create `useStorageState.ts` hook wrapping expo-secure-store (getItemAsync/setItemAsync/deleteItemAsync) with React state sync. Create `ctx.tsx` SessionProvider with signIn(url, apiKey)/signOut/session/isLoading via React Context, storing JSON `{instanceUrl, apiKey}` in secure storage. Follow the Expo docs SessionProvider pattern.
  - Verify: `cd mobile && npx tsc --noEmit` exits 0
  - Done when: All three modules compile cleanly, API client has connect/getCurrentContext/updateContext methods, SessionProvider exposes signIn/signOut/session

- [ ] **T03: Onboarding Screen & Route Guards** `est:30m`
  - Why: The sign-in flow and route protection are the first user-facing capability — without them, the app has no way to collect credentials or protect authenticated screens.
  - Files: `mobile/src/app/_layout.tsx`, `mobile/src/app/sign-in.tsx`
  - Do: Create root `_layout.tsx` that wraps the app in `<SessionProvider>`, renders `<Slot/>`. Create `(app)/_layout.tsx` (or inline in root layout) that checks `session` from `useSession()` — if null and not loading, redirect to `/sign-in`. Create `sign-in.tsx` with TextInput for instance URL (placeholder "https://sempkm.example.com"), TextInput for API key (secureTextEntry), "Connect" button that instantiates SemPKMClient, calls connect(), on success calls signIn(), on failure shows error (network error, 401 invalid key, wrong URL). Show ActivityIndicator during connection test. Input validation: URL must start with http:// or https://, API key must be non-empty.
  - Verify: `cd mobile && npx tsc --noEmit` exits 0; `grep -q "useSession" mobile/src/app/sign-in.tsx`
  - Done when: Sign-in screen collects URL + API key, tests connection, stores credentials on success, shows errors on failure; unauthenticated users are redirected to sign-in

- [ ] **T04: Dashboard, Tab Navigation & Settings** `est:30m`
  - Why: The dashboard and settings screens complete the mobile app's core functionality — displaying context and managing the connection.
  - Files: `mobile/src/app/(app)/(tabs)/_layout.tsx`, `mobile/src/app/(app)/(tabs)/index.tsx`, `mobile/src/app/(app)/(tabs)/zones.tsx`, `mobile/src/app/(app)/(tabs)/settings.tsx`
  - Do: Create tab layout with 3 tabs using `<Tabs>` from expo-router — Dashboard (home icon), Zones (map-pin icon), Settings (settings icon). Use `@expo/vector-icons` Ionicons for tab icons. Dashboard screen (`index.tsx`): fetch `GET /api/context/current` on mount via SemPKMClient (constructed from session credentials), display location_zone, activity, time_period, calendar_event with labels, show staleness indicator (green/yellow/red dot based on is_stale), show "No context" empty state if no context posted, implement pull-to-refresh via `RefreshControl`. Zones screen: simple placeholder text "Zones — coming in a future update" (ready for S04). Settings screen: show connected instance URL from session, show app version, "Sign Out" button calling signOut() from useSession().
  - Verify: `cd mobile && npx tsc --noEmit` exits 0; `test -f mobile/src/app/\(app\)/\(tabs\)/_layout.tsx && test -f mobile/src/app/\(app\)/\(tabs\)/index.tsx`
  - Done when: All 3 tabs render, dashboard fetches and displays context, settings shows connection info and sign-out works, zones shows placeholder

## Files Likely Touched

- `mobile/` — entire new Expo project directory
- `mobile/app.json` — Expo configuration
- `mobile/package.json` — dependencies
- `mobile/tsconfig.json` — TypeScript config
- `mobile/src/api/client.ts` — SemPKM API client
- `mobile/src/hooks/useStorageState.ts` — secure storage hook
- `mobile/src/ctx.tsx` — session/auth provider
- `mobile/src/app/_layout.tsx` — root layout with SessionProvider
- `mobile/src/app/sign-in.tsx` — onboarding screen
- `mobile/src/app/(app)/(tabs)/_layout.tsx` — tab navigator
- `mobile/src/app/(app)/(tabs)/index.tsx` — dashboard screen
- `mobile/src/app/(app)/(tabs)/zones.tsx` — zones placeholder
- `mobile/src/app/(app)/(tabs)/settings.tsx` — settings screen
- `.gitignore` — mobile artifact exclusions
