# S03 Research: Mobile App Foundation & API Connection

## Summary

S03 creates the first React Native mobile surface for SemPKM — an Expo project in `mobile/` that connects to the backend via Bearer token API, stores credentials securely, and displays current context state. This is a **deep research** slice: React Native/Expo is entirely new to this codebase, with zero prior experience. Every pattern must be established from scratch.

**Key finding:** Expo SDK 55 (released Feb 25, 2026, latest stable) provides the exact primitives needed — `expo-secure-store` for credential storage, `expo-router` v7 for file-based tab navigation, and a managed workflow with development builds that supports all native modules S04-S06 will need (geofencing, notifications, calendar). The existing backend already exposes every endpoint the mobile app consumes.

**Risk assessment:** The primary risk is the build toolchain itself (Metro bundler, native compilation, EAS). The API integration is low-risk because the backend auth and context endpoints are already proven by S01-S02 tests and the browser extension. The mobile app is a thin client.

## Relevant Requirements

S03 is the primary owner of these requirements from the M037 scope:

- **CTX-07** (implied): Mobile app connects to SemPKM instance via API key
- **CTX-08** (implied): Mobile app displays current context state
- **CTX-19** (implied, deferred): Version checking — the `.well-known/sempkm` response includes `version` field which can be compared

S03 supports (produces infrastructure for):
- CTX-09 (S04): Geofence zone monitoring — S03 delivers the API client and navigation scaffold
- CTX-10 (S05): Calendar reading — S03 delivers the context update dispatch function
- CTX-11 (S06): Push notification display — S03 delivers the Expo project with notification capability

## Recommendation

**Use Expo SDK 55 with the default template (`--template default@sdk-55`), TypeScript, expo-router v7, and expo-secure-store.** Initialize in `mobile/` as a standalone Expo project, not in the project root. The API client should be a TypeScript class mirroring the extension's `SemPKMClient` pattern. Use the Expo docs' `SessionProvider` + `useStorageState` pattern for auth state management.

SDK 55 is preferred over SDK 54 because:
1. SDK 55 is the latest stable (React Native 0.83, React 19.2)
2. New Architecture is the default (and only option) — avoids future migration
3. New `/src/app` project structure is cleaner
4. Development builds are recommended and will be required for S04 (geofencing)

**Do NOT use Expo Go** — it stays on SDK 54 during the transition and doesn't support native modules needed in S04+. Use development builds from day one.

## Implementation Landscape

### What Exists (Backend — Consumed by S03)

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /.well-known/sempkm` | Connection test — returns version, endpoints, capabilities | Bearer token |
| `GET /api/context/current` | Current context with `is_stale` flag | Bearer token |
| `POST /api/context/update` | Push context snapshot (location_zone, activity, time_period, calendar_event, calendar_busy, device_id) | Bearer token, rate-limited 12/min |
| `GET /api/context/stream` | SSE stream for real-time context events | Bearer token |

All endpoints use `get_current_user_or_api` which accepts `Authorization: Bearer {api_key}` header. The mobile app authenticates identically to the browser extension.

### What Exists (Extension API Client — Pattern Reference)

`extension/shared/api-client.js` provides the `SemPKMClient` class:
- Constructor: `(instanceUrl, apiKey)` — strips trailing slash
- `_headers()` → `Authorization: Bearer {key}`, `Content-Type: application/json`
- `_request(path, options)` → unified fetch + error handling with `SemPKMError`
- `connect()` → `GET /.well-known/sempkm` (connection test)
- Typed error with HTTP status and parsed detail

This maps directly to a TypeScript class. The mobile client needs: `connect()`, `getCurrentContext()`, `updateContext()`. S04 adds `getZones()`/`createZone()` etc.

### What Must Be Created

| Component | Location | Notes |
|-----------|----------|-------|
| Expo project scaffold | `mobile/` | `npx create-expo-app@latest --template default@sdk-55` |
| App config | `mobile/app.json` or `mobile/app.config.ts` | Bundle ID: `app.sempkm.mobile`, slug: `sempkm` |
| API client | `mobile/src/api/client.ts` | TypeScript, mirrors SemPKMClient pattern |
| Secure storage hook | `mobile/src/hooks/useStorageState.ts` | expo-secure-store + React Context (Expo docs pattern) |
| Session provider | `mobile/src/ctx.tsx` | AuthContext with signIn/signOut/session |
| Root layout | `mobile/src/app/_layout.tsx` | SessionProvider wrapper + auth route guard |
| Sign-in screen | `mobile/src/app/sign-in.tsx` | Instance URL + API key inputs + connection test |
| Tab layout | `mobile/src/app/(app)/(tabs)/_layout.tsx` | Dashboard, Zones, Settings tabs |
| Dashboard screen | `mobile/src/app/(app)/(tabs)/index.tsx` | Displays current context from API |
| Zones placeholder | `mobile/src/app/(app)/(tabs)/zones.tsx` | Empty screen ready for S04 |
| Settings screen | `mobile/src/app/(app)/(tabs)/settings.tsx` | Shows connection info, sign-out button |
| .gitignore additions | `.gitignore` | `.expo/`, `mobile/android/`, `mobile/ios/` |

### Project Structure (SDK 55 Convention)

```
mobile/
├── app.json                    # Expo config
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
├── src/
│   ├── app/
│   │   ├── _layout.tsx         # Root layout (SessionProvider + route guards)
│   │   ├── sign-in.tsx         # Onboarding screen
│   │   └── (app)/
│   │       └── (tabs)/
│   │           ├── _layout.tsx # Tab navigator
│   │           ├── index.tsx   # Dashboard
│   │           ├── zones.tsx   # Zones (S04 placeholder)
│   │           └── settings.tsx # Settings
│   ├── api/
│   │   └── client.ts           # SemPKMClient TypeScript port
│   ├── hooks/
│   │   └── useStorageState.ts  # Secure credential storage
│   └── ctx.tsx                 # SessionProvider + useSession
├── assets/                     # Icons, splash screen
└── .gitignore
```

## Key Technical Patterns

### 1. Authentication Flow (Expo Router Pattern)

The Expo docs recommend a `SessionProvider` + `useStorageState` hook pattern:

1. `useStorageState(key)` wraps `expo-secure-store` on native / `localStorage` on web
2. `SessionProvider` exposes `signIn(url, key)` / `signOut()` / `session` / `isLoading`
3. Root `_layout.tsx` wraps app in `<SessionProvider>`
4. `(app)/_layout.tsx` checks `session` — redirects to `/sign-in` if null
5. Sign-in screen collects URL + API key, tests connection, stores credentials

**Adaptation for SemPKM:** The session stores a JSON string: `{ instanceUrl, apiKey }`. Unlike typical auth flows, there's no OAuth — the user pastes an API key generated in the SemPKM Settings → API Keys page (M013).

### 2. API Client Pattern

```typescript
// mobile/src/api/client.ts
export class SemPKMClient {
  constructor(private instanceUrl: string, private apiKey: string) {
    this.instanceUrl = instanceUrl.replace(/\/+$/, '');
  }

  private headers(): HeadersInit {
    return {
      'Authorization': `Bearer ${this.apiKey}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
  }

  async request<T>(path: string, options?: RequestInit): Promise<T> {
    const url = `${this.instanceUrl}${path}`;
    const response = await fetch(url, { ...options, headers: this.headers() });
    if (!response.ok) {
      const detail = await response.json().catch(() => ({ detail: response.statusText }));
      throw new SemPKMError(response.status, detail.detail ?? 'Unknown error');
    }
    return response.json();
  }

  connect() { return this.request<InstanceInfo>('/.well-known/sempkm'); }
  getCurrentContext() { return this.request<ContextResponse>('/api/context/current'); }
  updateContext(data: ContextUpdate) {
    return this.request<ContextData>('/api/context/update', {
      method: 'POST', body: JSON.stringify(data),
    });
  }
}
```

### 3. Onboarding Flow

1. User opens app → sees sign-in screen (no session stored)
2. Enters SemPKM instance URL (e.g., `https://sempkm.example.com` or `http://192.168.1.100:3000`)
3. Enters API key (generated from SemPKM Settings → API Keys)
4. Taps "Connect" → app calls `client.connect()` (GET /.well-known/sempkm)
5. On success: store `{ instanceUrl, apiKey }` in expo-secure-store, navigate to dashboard
6. On failure: show error (network unreachable, invalid key, wrong URL)

### 4. Dashboard Screen

Fetches `GET /api/context/current` on mount and displays:
- Location zone (or "Not set")
- Activity (or "Not set")
- Time period (or "Not set")
- Calendar event (or "None")
- Staleness indicator (green dot = fresh, yellow = approaching stale, red = stale)
- Last updated timestamp
- Pull-to-refresh gesture

## Dependencies

### Required npm packages (installed via `npx expo install`)

| Package | Purpose | Version constraint |
|---------|---------|-------------------|
| `expo` | Core SDK | ~55.0.0 |
| `expo-router` | File-based routing | ~5.0.0 (bundled with SDK 55) |
| `expo-secure-store` | Encrypted credential storage | ~14.0.0 |
| `react-native-safe-area-context` | Safe area insets | Bundled |
| `react-native-screens` | Screen optimization | Bundled |
| `@expo/vector-icons` | Tab bar icons | Bundled |

These are the S03 minimum. S04 adds `expo-location`, `expo-task-manager`. S05 adds `expo-calendar`, `expo-sensors`. S06 adds `expo-notifications`.

### Development tooling

| Tool | Purpose |
|------|---------|
| Metro bundler | JS bundling (started via `npx expo start`) |
| `expo-dev-client` | Development builds (required for native modules) |
| TypeScript | Type safety |
| EAS CLI | Build service (for creating development builds) |

## Constraints & Gotchas

### 1. SDK 55 Transition Period
During the transition, `create-expo-app@latest` without `--template` creates SDK 54. **Must use `--template default@sdk-55`** explicitly.

### 2. Development Builds vs Expo Go
Expo Go on physical iOS devices stays on SDK 54. For SDK 55, use:
- iOS Simulator: Expo Go SDK 55 installed via CLI
- Physical iOS: TestFlight external beta or `eas go` command
- Android: Install Expo Go SDK 55 from CLI

For S04+ (geofencing), Expo Go won't work at all — development builds are required. S03 should establish the dev build pipeline even though the basic screens could work in Expo Go.

### 3. Network Configuration
The mobile device must reach the SemPKM backend. Common scenarios:
- **Local dev:** Backend at `http://192.168.x.x:3000` — iOS requires `NSAppTransportSecurity` exception for HTTP
- **Deployed:** Backend at `https://sempkm.example.com` — works out of the box
- **Docker:** Backend at `http://localhost:3000` — only works on simulator, not physical device

The onboarding screen should accept any URL and warn if HTTP (not HTTPS).

### 4. Monorepo Considerations
The `mobile/` directory is a standalone Expo project with its own `package.json` and `node_modules/`. It is NOT integrated into the root project's package.json. This avoids Metro bundler conflicts with the backend Python project and the extension's vanilla JS.

### 5. .gitignore Additions
```
# Mobile app (Expo)
mobile/.expo/
mobile/node_modules/
mobile/android/
mobile/ios/
mobile/dist/
```

The `android/` and `ios/` directories are generated by `npx expo prebuild` and should not be committed (managed workflow convention).

## Verification Strategy

### Build Verification
1. `cd mobile && npx expo start` — Metro bundler starts without errors
2. TypeScript: `npx tsc --noEmit` — zero type errors
3. App loads on iOS Simulator or Android Emulator

### Functional Verification
1. App shows sign-in screen on first launch (no stored credentials)
2. Entering valid URL + API key → connection test succeeds → navigates to dashboard
3. Entering invalid URL → shows network error
4. Entering invalid API key → shows 401 error
5. Dashboard shows current context (or "No context" if none posted)
6. Pull-to-refresh on dashboard fetches fresh context
7. Tab navigation works (Dashboard ↔ Zones ↔ Settings)
8. Settings screen shows connected instance URL
9. Sign out → returns to sign-in screen → credentials cleared from secure storage
10. Re-launch app → auto-signs in (credentials persisted)

### Integration Verification
- With Docker stack running: mobile app → POST context update → verify via GET /api/context/current in browser

## Don't Hand-Roll

| Pattern | Use instead |
|---------|-------------|
| Custom navigation | expo-router (file-based, proven) |
| Credential storage | expo-secure-store (Keychain/EncryptedSharedPrefs) |
| Tab navigation | Expo Router `<Tabs>` component |
| HTTP client | Native `fetch()` with wrapper class (no axios needed) |
| Auth state management | React Context + useStorageState hook (Expo docs pattern) |
| Route protection | Expo Router `<Redirect>` or `Stack.Protected` guard |

## Suggested Skills

The following skills are available and directly relevant for S03 implementation:

| Skill | Install Command | Installs | Relevance |
|-------|----------------|----------|-----------|
| `vercel-react-native-skills` | `npx skills add vercel-labs/agent-skills@vercel-react-native-skills` | 68.9K | React Native best practices from Vercel |
| `react-native-best-practices` | `npx skills add callstackincubator/agent-skills@react-native-best-practices` | 8.2K | Callstack's RN patterns |
| `building-native-ui` | `npx skills add expo/skills@building-native-ui` | 20.9K | Expo's own UI skill |
| `native-data-fetching` | `npx skills add expo/skills@native-data-fetching` | 15.4K | Expo data fetching patterns |

**Recommendation:** Install `vercel-labs/agent-skills@vercel-react-native-skills` and `expo/skills@building-native-ui` — they have the highest install counts and are most relevant to S03's React Native + Expo work.

## Task Decomposition Guidance

Natural seams for the planner:

1. **T01: Expo Project Scaffold** — `create-expo-app`, configure `app.json`, install `expo-secure-store`, set up TypeScript, add `.gitignore` entries. This is the riskiest task (build toolchain). Verify: `npx expo start` succeeds.

2. **T02: API Client + Auth Provider** — `client.ts` (SemPKMClient port), `useStorageState.ts` hook, `ctx.tsx` SessionProvider. These are pure TypeScript modules with no UI. Verify: TypeScript compiles clean.

3. **T03: Onboarding Screen + Route Guards** — Sign-in screen with URL/key inputs, connection test button, error display. Root layout with SessionProvider and auth redirect. Verify: app navigates between sign-in and main screens based on auth state.

4. **T04: Dashboard + Tab Navigation + Settings** — Tab layout with Dashboard/Zones/Settings, context display screen, settings with connection info and sign-out. Verify: full flow — sign in → see context → navigate tabs → sign out.

**Riskiest-first:** T01 must succeed before anything else — if the Expo build chain doesn't work, nothing else matters. T02 has no UI risk. T03 and T04 are standard React Native screens.

## Sources

- Expo SDK 55 changelog: https://expo.dev/changelog/sdk-55
- Expo Router authentication: https://docs.expo.dev/router/advanced/authentication/
- Expo SecureStore: https://docs.expo.dev/versions/latest/sdk/securestore/
- create-expo-app docs: https://docs.expo.dev/more/create-expo/
- Extension API client pattern: `extension/shared/api-client.js`
- Backend auth: `backend/app/auth/dependencies.py` (`get_current_user_or_api`)
- Context API: `backend/app/context/router.py` (S01)
- Context service: `backend/app/context/service.py` (S01)
