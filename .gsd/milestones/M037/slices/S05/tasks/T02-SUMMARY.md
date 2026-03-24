---
id: T02
parent: S05
milestone: M037
provides:
  - activity.ts service with startActivityMonitoring(), stopActivityMonitoring(), getCurrentActivity()
  - ActivityType type alias exported for use by orchestrator hook
key_files:
  - mobile/src/services/activity.ts
key_decisions:
  - Round variance to 4 decimal places in diagnostic logs for readability without losing useful precision
  - Pedometer snapshot interval of 3 seconds balances responsiveness vs false positives from individual step-count jitter
patterns_established:
  - Activity service follows calendar.ts/geofencing.ts pattern: module-scope state, domain-prefixed console.log keys, typed return values
  - Sliding window with population variance for sensor signal smoothing — reusable pattern for any future sensor-based classification
observability_surfaces:
  - console.log activity.monitoring_started { pedometerAvailable } — subscription lifecycle
  - console.log activity.classified { activity, variance, windowSize, stepsIncreasing } — each classification update
  - console.log activity.hardware_unavailable — accelerometer not present, permanent degradation to unknown
  - console.log activity.pedometer_unavailable — pedometer not present, accelerometer-only mode
  - console.log activity.monitoring_stopped — cleanup confirmation
duration: 8m
verification_result: passed
completed_at: 2026-03-23
blocker_discovered: false
---

# T02: Activity detection service with accelerometer and pedometer

**Built activity detection service that classifies stationary/walking/driving via accelerometer magnitude variance over a 10-sample sliding window at 1Hz, with pedometer step-count override for walking ground truth.**

## What Happened

Created `mobile/src/services/activity.ts` following the established service pattern from geofencing.ts and calendar.ts. The service implements:

- **Accelerometer subscription at 1Hz** — `setUpdateInterval(1000)` feeds `onAccelerometerData()` which computes magnitude (`sqrt(x²+y²+z²)`), maintains a 10-element sliding window, and classifies when the window is full.
- **Variance-based classification** — population variance of the magnitude window maps to thresholds: `<0.01` → stationary, `0.01–0.15` → walking, `≥0.15` → driving.
- **Pedometer walking override** — `Pedometer.watchStepCount()` tracks cumulative steps. Every 3+ seconds, if the step count increased since the last snapshot, classification is overridden to "walking" regardless of variance. This handles the case where walking in a straight line at steady pace produces low variance but step count is unambiguous.
- **Graceful degradation** — if `Accelerometer.isAvailableAsync()` returns false, the service logs `activity.hardware_unavailable` once and returns "unknown" permanently. If pedometer is unavailable, classification proceeds on accelerometer alone.
- **Idempotent start** — `startActivityMonitoring()` checks for existing subscription and returns immediately if already monitoring.
- **Clean stop** — `stopActivityMonitoring()` removes both subscriptions, clears the sliding window, and resets all pedometer tracking state.

## Verification

All task-level and applicable slice-level verification checks pass:
- `npx tsc --noEmit` — zero TypeScript errors
- `activity.ts` exists and exports all four required symbols
- Sliding window implemented at 10 samples with variance computation
- Three-tier classification thresholds match spec exactly
- Pedometer snapshot comparison implemented with 3-second interval
- Idempotent guard on `_accelSubscription !== null` check

Slice checks not yet applicable: `time-period.ts` (T03), `useContextServices.ts` (T04), orchestrator wiring (T04) — expected.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd mobile && npx tsc --noEmit` | 0 | ✅ pass | 3.2s |
| 2 | `test -f mobile/src/services/activity.ts` | 0 | ✅ pass | <1s |
| 3 | `grep -q 'startActivityMonitoring' mobile/src/services/activity.ts` | 0 | ✅ pass | <1s |
| 4 | `grep -q 'getCurrentActivity' mobile/src/services/activity.ts` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'stopActivityMonitoring' mobile/src/services/activity.ts` | 0 | ✅ pass | <1s |
| 6 | `grep -q '"expo-sensors"' mobile/package.json` | 0 | ✅ pass | <1s |
| 7 | `grep -q 'expo-calendar' mobile/app.json` | 0 | ✅ pass | <1s |

## Diagnostics

- **Classification state:** Call `getCurrentActivity()` — returns latest `ActivityType`. Visible in React DevTools via the orchestrator hook (T04).
- **Variance monitoring:** Filter Expo dev tools by `activity.classified` to see real-time variance values and classification decisions.
- **Hardware diagnostics:** `activity.hardware_unavailable` appears exactly once if accelerometer is missing. `activity.pedometer_unavailable` appears if pedometer is missing but accelerometer works.
- **Lifecycle:** `activity.monitoring_started` and `activity.monitoring_stopped` bracket the monitoring session.

## Deviations

None. Implementation matches the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `mobile/src/services/activity.ts` — New activity detection service with accelerometer sliding window, variance classification, and pedometer walking override
- `.gsd/milestones/M037/slices/S05/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
