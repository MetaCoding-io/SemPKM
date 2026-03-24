---
estimated_steps: 4
estimated_files: 1
skills_used: []
---

# T02: Activity detection service with accelerometer and pedometer

**Slice:** S05 — Mobile Calendar & Activity Detection
**Milestone:** M037

## Description

Build the activity detection service that classifies user activity as stationary/walking/driving using accelerometer magnitude variance over a sliding window, supplemented by pedometer step counting. This directly addresses requirement CTX-13: "Mobile app detects activity type (stationary/walking/driving)."

The accelerometer reports `{ x, y, z }` in g-forces. Magnitude = `sqrt(x² + y² + z²)`. At rest, magnitude ≈ 1.0g. Movement creates variance. The service maintains a 10-sample sliding window at 1Hz, computes variance, and classifies:
- Variance < 0.01 → stationary
- Variance 0.01–0.15 → walking
- Variance ≥ 0.15 → driving/vehicle

Pedometer provides a "walking" ground truth — if step count is increasing, override to "walking" regardless of variance. When hardware is unavailable (`Accelerometer.isAvailableAsync()` returns false), the service degrades to returning "unknown".

Note: `expo-sensors` was installed in T01. This task only creates the service file.

## Steps

1. Create `mobile/src/services/activity.ts` with the following exports:
   - `ActivityType` — type alias: `'stationary' | 'walking' | 'driving' | 'unknown'`
   - `startActivityMonitoring()` — checks `Accelerometer.isAvailableAsync()`. If unavailable, sets activity to "unknown" and returns. Otherwise: sets Accelerometer update interval to 1000ms (1Hz), subscribes to `Accelerometer.addListener()`, pushes magnitude (`sqrt(x² + y² + z²)`) to a 10-element sliding window array, computes variance when window is full. Also starts `Pedometer.watchStepCount()` to track step increases.
   - `stopActivityMonitoring()` — removes Accelerometer listener subscription and Pedometer subscription. Clears the sliding window.
   - `getCurrentActivity()` — returns the most recently classified `ActivityType`.

2. Implement the sliding window and variance computation:
   - Module-level array `magnitudeWindow: number[]` (max 10 elements).
   - On each accelerometer event: compute `Math.sqrt(x*x + y*y + z*z)`, push to window, shift if length > 10.
   - Compute variance: `mean = sum/N`, `variance = sum((xi - mean)²) / N`.
   - Classify based on thresholds. If pedometer shows steps increasing (compare current step count to previous snapshot taken 3+ seconds ago), override classification to "walking".

3. Handle edge cases:
   - Accelerometer unavailable → "unknown" permanently
   - Window not yet full (< 10 samples) → "unknown" until enough data
   - Pedometer unavailable → classification works on accelerometer alone (no override)
   - Already monitoring → `startActivityMonitoring()` is idempotent (no double subscriptions)

4. Verify TypeScript compiles: `cd mobile && npx tsc --noEmit`.

## Must-Haves

- [ ] `activity.ts` exports `ActivityType`, `startActivityMonitoring`, `stopActivityMonitoring`, `getCurrentActivity`
- [ ] Accelerometer subscription at 1Hz with magnitude sliding window (10 samples)
- [ ] Variance-based classification: stationary (< 0.01), walking (0.01–0.15), driving (≥ 0.15)
- [ ] Pedometer step-count supplement overrides to "walking" when steps increasing
- [ ] Graceful degradation to "unknown" when accelerometer unavailable
- [ ] Idempotent start (no double subscriptions)
- [ ] TypeScript compiles with zero errors

## Verification

- `cd mobile && npx tsc --noEmit` — zero errors
- `test -f mobile/src/services/activity.ts` — file exists
- `grep -q 'startActivityMonitoring' mobile/src/services/activity.ts` — export present
- `grep -q 'getCurrentActivity' mobile/src/services/activity.ts` — export present

## Inputs

- `mobile/package.json` — has `expo-sensors` installed (from T01)
- `mobile/src/services/geofencing.ts` — reference pattern for service module structure

## Observability Impact

**New signals:**
- `activity.monitoring_started` — logged when accelerometer subscription begins, includes `{ pedometerAvailable: boolean }`
- `activity.hardware_unavailable` — logged once if `Accelerometer.isAvailableAsync()` returns false; service degrades to "unknown"
- `activity.classified` — logged on each classification update with `{ activity, variance, windowSize, stepsIncreasing }`
- `activity.monitoring_stopped` — logged when subscriptions are removed

**Inspection surface:**
- `getCurrentActivity()` returns the latest `ActivityType` — visible in React DevTools via the orchestrator hook
- Module-level state is self-contained: `magnitudeWindow`, `currentActivity`, `lastStepCount`, subscription references

**Failure visibility:**
- Hardware unavailable → single `activity.hardware_unavailable` log entry, `getCurrentActivity()` returns "unknown" permanently
- Pedometer unavailable → `activity.pedometer_unavailable` log, classification proceeds on accelerometer alone
- Double-start guard → `startActivityMonitoring()` is idempotent, no diagnostic noise from duplicate calls

## Expected Output

- `mobile/src/services/activity.ts` — new file with activity classification via accelerometer + pedometer
