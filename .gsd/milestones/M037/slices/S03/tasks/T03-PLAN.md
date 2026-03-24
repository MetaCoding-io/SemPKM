---
estimated_steps: 4
estimated_files: 3
skills_used:
  - react-best-practices
---

# T03: Onboarding Screen & Route Guards

**Slice:** S03 — Mobile App Foundation & API Connection
**Milestone:** M037

## Description

Create the sign-in screen and route protection. Unauthenticated users see the onboarding screen where they enter their SemPKM instance URL and API key. On successful connection test, credentials are stored securely and the user is routed to the main app. Error states (network unreachable, invalid key, wrong URL) are displayed clearly.

## Steps

1. Create `mobile/src/app/_layout.tsx` — root layout:
   - Import `SessionProvider` from `../ctx`
   - Import `Slot` from `expo-router`
   - Render `<SessionProvider><Slot /></SessionProvider>`
   - This wraps the entire app in the auth context

2. Create `mobile/src/app/(app)/_layout.tsx` — authenticated route guard:
   - Import `useSession` from `../../ctx`
   - Import `Redirect`, `Slot` from `expo-router`
   - Import `Text`, `View` from `react-native`
   - If `isLoading`, render a loading spinner/text ("Loading...")
   - If `!session`, render `<Redirect href="/sign-in" />`
   - Otherwise render `<Slot />`

3. Create `mobile/src/app/sign-in.tsx` — onboarding screen:
   - Import `useSession` from `../ctx`, `SemPKMClient` from `../api/client`, `router` from `expo-router`
   - State: `instanceUrl: string`, `apiKey: string`, `error: string | null`, `connecting: boolean`
   - TextInput for instance URL with placeholder "https://sempkm.example.com", autoCapitalize="none", autoCorrect=false, keyboardType="url"
   - TextInput for API key with secureTextEntry=true, placeholder "Enter your API key"
   - "Connect" button (disabled when `connecting` or inputs empty):
     - Validate URL starts with `http://` or `https://`; show error if not
     - Set connecting=true, clear error
     - Create `new SemPKMClient(instanceUrl, apiKey)`, call `await client.connect()`
     - On success: call `signIn(instanceUrl, apiKey)` from useSession (this stores credentials and triggers redirect via route guard)
     - On SemPKMError: show `error.detail` (e.g., "Not authenticated" for 401)
     - On network error: show "Could not reach server. Check the URL and your network connection."
     - Set connecting=false in finally block
   - Show error text in red below the button when `error` is set
   - Show ActivityIndicator when `connecting` is true
   - Basic styling: centered form, padding, reasonable font sizes

4. Verify TypeScript compiles: `cd mobile && npx tsc --noEmit`

## Must-Haves

- [ ] Root layout wraps app in SessionProvider
- [ ] `(app)/_layout.tsx` redirects to `/sign-in` when no session
- [ ] Sign-in screen has URL input, API key input, and Connect button
- [ ] Connection test calls `GET /.well-known/sempkm` via SemPKMClient.connect()
- [ ] Success stores credentials and navigates to main app
- [ ] Errors displayed: invalid URL format, network unreachable, 401 invalid key
- [ ] Loading state shown during connection test
- [ ] Zero TypeScript errors

## Verification

- `cd mobile && npx tsc --noEmit` exits with code 0
- `grep -q "useSession" mobile/src/app/sign-in.tsx` — uses auth context
- `grep -q "SemPKMClient" mobile/src/app/sign-in.tsx` — uses API client
- `grep -q "Redirect" mobile/src/app/\(app\)/_layout.tsx` — route guard redirects

## Inputs

- `mobile/src/api/client.ts` — SemPKMClient for connection test (from T02)
- `mobile/src/ctx.tsx` — SessionProvider and useSession (from T02)
- `mobile/src/hooks/useStorageState.ts` — secure storage hook (from T02)

## Expected Output

- `mobile/src/app/_layout.tsx` — root layout with SessionProvider
- `mobile/src/app/sign-in.tsx` — onboarding screen with connection test
- `mobile/src/app/(app)/_layout.tsx` — authenticated route guard
