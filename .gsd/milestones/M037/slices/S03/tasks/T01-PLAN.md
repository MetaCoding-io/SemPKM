---
estimated_steps: 5
estimated_files: 5
skills_used:
  - react-best-practices
---

# T01: Expo Project Scaffold & Build Verification

**Slice:** S03 — Mobile App Foundation & API Connection
**Milestone:** M037

## Description

Scaffold the Expo SDK 55 project in `mobile/`, configure app identity, install `expo-secure-store`, add `.gitignore` entries, and prove the build toolchain works (Metro bundler starts, TypeScript compiles). This is the riskiest task in S03 — everything downstream depends on a working Expo project.

## Steps

1. Run `npx create-expo-app@latest mobile --template default@sdk-55` from the project root to create the Expo project. If the `--template default@sdk-55` flag doesn't work (template naming may differ), try `--template blank-typescript@sdk-55` or just `npx create-expo-app@latest mobile` and verify SDK version in package.json.
2. Edit `mobile/app.json` to set: `name: "SemPKM"`, `slug: "sempkm"`, `scheme: "sempkm"`, `ios.bundleIdentifier: "app.sempkm.mobile"`, `android.package: "app.sempkm.mobile"`. Preserve all other default fields.
3. Install `expo-secure-store`: run `cd mobile && npx expo install expo-secure-store` (the `expo install` command ensures version compatibility with the SDK).
4. Append mobile-specific entries to the root `.gitignore` file (at `/home/james/Code/SemPKM/.gitignore`):
   ```
   # Mobile app (Expo)
   mobile/.expo/
   mobile/node_modules/
   mobile/android/
   mobile/ios/
   mobile/dist/
   ```
5. Verify the build toolchain: run `cd mobile && npx tsc --noEmit` (should exit 0) and `cd mobile && npx expo start --no-dev --non-interactive` (should print Metro server ready message within 30s, then Ctrl+C).

## Must-Haves

- [ ] `mobile/` directory contains a valid Expo SDK 55 project with `package.json`, `app.json`, `tsconfig.json`
- [ ] `app.json` has correct app identity (name, slug, scheme, bundleIdentifier, package)
- [ ] `expo-secure-store` appears in `mobile/package.json` dependencies
- [ ] Root `.gitignore` has entries for `mobile/.expo/`, `mobile/node_modules/`, `mobile/android/`, `mobile/ios/`, `mobile/dist/`
- [ ] `npx tsc --noEmit` exits 0
- [ ] Metro bundler starts without errors

## Verification

- `cd mobile && npx tsc --noEmit` exits with code 0
- `cd mobile && timeout 30 npx expo start --no-dev --non-interactive 2>&1 | grep -i "metro\|ready\|started\|waiting"` — shows Metro server startup
- `grep -q "expo-secure-store" mobile/package.json` — dependency installed
- `grep -q "mobile/.expo/" .gitignore` — gitignore updated

## Inputs

- `extension/shared/api-client.js` — reference pattern for API client (not modified, read for context only)
- `.gitignore` — append mobile entries

## Expected Output

- `mobile/app.json` — Expo project configuration with app identity
- `mobile/package.json` — dependencies including expo-secure-store
- `mobile/tsconfig.json` — TypeScript configuration
- `.gitignore` — updated with mobile artifact exclusions
