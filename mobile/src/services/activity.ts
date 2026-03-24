/**
 * Activity detection service for SemPKM mobile context detection.
 *
 * Classifies user activity as stationary/walking/driving using
 * accelerometer magnitude variance over a 10-sample sliding window
 * at 1Hz, supplemented by pedometer step counting as a walking
 * ground-truth signal.
 *
 * Classification thresholds (magnitude variance):
 *   < 0.01           → stationary
 *   0.01 – 0.15      → walking
 *   ≥ 0.15           → driving
 *
 * Pedometer override: if step count is increasing (compared to a
 * snapshot taken ≥3 seconds ago), classification is forced to
 * "walking" regardless of accelerometer variance.
 *
 * Diagnostic keys (for Expo dev tools filtering):
 *   activity.monitoring_started      — accelerometer subscription active
 *   activity.monitoring_stopped      — subscriptions removed
 *   activity.hardware_unavailable    — accelerometer not available; degraded to "unknown"
 *   activity.pedometer_unavailable   — pedometer not available; accelerometer-only mode
 *   activity.classified              — classification update with variance + activity
 *
 * @module services/activity
 */

import { Accelerometer, Pedometer, type AccelerometerMeasurement } from 'expo-sensors';
import type { EventSubscription } from 'expo-modules-core';

// ── Types ───────────────────────────────────────────────────────

export type ActivityType = 'stationary' | 'walking' | 'driving' | 'unknown';

// ── Classification thresholds ───────────────────────────────────

const VARIANCE_STATIONARY_MAX = 0.01;
const VARIANCE_WALKING_MAX = 0.15;
const WINDOW_SIZE = 10;
const STEP_SNAPSHOT_INTERVAL_MS = 3000;

// ── Module-level state ──────────────────────────────────────────

let _accelSubscription: EventSubscription | null = null;
let _pedometerSubscription: EventSubscription | null = null;

let _magnitudeWindow: number[] = [];
let _currentActivity: ActivityType = 'unknown';

/** Pedometer step tracking for walking override */
let _currentStepCount = 0;
let _snapshotStepCount = 0;
let _snapshotTimestamp = 0;
let _stepsIncreasing = false;

// ── Internal helpers ────────────────────────────────────────────

/**
 * Compute population variance of an array of numbers.
 */
function computeVariance(values: number[]): number {
  const n = values.length;
  if (n === 0) return 0;
  const mean = values.reduce((sum, v) => sum + v, 0) / n;
  return values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / n;
}

/**
 * Classify activity based on magnitude variance and pedometer data.
 */
function classify(variance: number): ActivityType {
  // Pedometer override: if steps are increasing, user is walking
  if (_stepsIncreasing) {
    return 'walking';
  }

  if (variance < VARIANCE_STATIONARY_MAX) {
    return 'stationary';
  }
  if (variance < VARIANCE_WALKING_MAX) {
    return 'walking';
  }
  return 'driving';
}

/**
 * Handle a new accelerometer measurement.
 */
function onAccelerometerData(data: AccelerometerMeasurement): void {
  const magnitude = Math.sqrt(data.x * data.x + data.y * data.y + data.z * data.z);

  // Push to sliding window, trim to max size
  _magnitudeWindow.push(magnitude);
  if (_magnitudeWindow.length > WINDOW_SIZE) {
    _magnitudeWindow.shift();
  }

  // Don't classify until window is full
  if (_magnitudeWindow.length < WINDOW_SIZE) {
    return;
  }

  const variance = computeVariance(_magnitudeWindow);
  _currentActivity = classify(variance);

  console.log('activity.classified', {
    activity: _currentActivity,
    variance: Math.round(variance * 10000) / 10000,
    windowSize: _magnitudeWindow.length,
    stepsIncreasing: _stepsIncreasing,
  });
}

/**
 * Handle a pedometer step count update.
 * Compares current step count to a snapshot taken ≥3 seconds ago
 * to determine if the user is actively walking.
 */
function onStepCountUpdate(result: { steps: number }): void {
  _currentStepCount = result.steps;

  const now = Date.now();
  if (_snapshotTimestamp === 0) {
    // First reading — initialize snapshot
    _snapshotStepCount = _currentStepCount;
    _snapshotTimestamp = now;
    _stepsIncreasing = false;
    return;
  }

  // Only compare after the snapshot interval has elapsed
  if (now - _snapshotTimestamp >= STEP_SNAPSHOT_INTERVAL_MS) {
    _stepsIncreasing = _currentStepCount > _snapshotStepCount;
    // Update snapshot for next comparison
    _snapshotStepCount = _currentStepCount;
    _snapshotTimestamp = now;
  }
}

// ── Exported functions ──────────────────────────────────────────

/**
 * Start activity monitoring using accelerometer and pedometer.
 *
 * Idempotent — calling while already monitoring is a no-op.
 * Degrades to "unknown" if accelerometer hardware is unavailable.
 * Operates on accelerometer alone if pedometer is unavailable.
 */
export async function startActivityMonitoring(): Promise<void> {
  // Idempotent guard — don't double-subscribe
  if (_accelSubscription !== null) {
    return;
  }

  // Check accelerometer availability
  const accelAvailable = await Accelerometer.isAvailableAsync();
  if (!accelAvailable) {
    _currentActivity = 'unknown';
    console.log('activity.hardware_unavailable', 'Accelerometer not available — activity detection disabled');
    return;
  }

  // Set 1Hz update interval (1000ms)
  Accelerometer.setUpdateInterval(1000);

  // Subscribe to accelerometer data
  _accelSubscription = Accelerometer.addListener(onAccelerometerData);

  // Try to start pedometer (supplemental — not required)
  let pedometerAvailable = false;
  try {
    pedometerAvailable = await Pedometer.isAvailableAsync();
    if (pedometerAvailable) {
      _pedometerSubscription = Pedometer.watchStepCount(onStepCountUpdate);
    } else {
      console.log('activity.pedometer_unavailable', 'Pedometer not available — using accelerometer only');
    }
  } catch {
    console.log('activity.pedometer_unavailable', 'Pedometer check failed — using accelerometer only');
  }

  console.log('activity.monitoring_started', { pedometerAvailable });
}

/**
 * Stop activity monitoring and clean up subscriptions.
 *
 * Resets all internal state so a subsequent start begins fresh.
 */
export function stopActivityMonitoring(): void {
  if (_accelSubscription !== null) {
    _accelSubscription.remove();
    _accelSubscription = null;
  }

  if (_pedometerSubscription !== null) {
    _pedometerSubscription.remove();
    _pedometerSubscription = null;
  }

  // Reset sliding window and classification state
  _magnitudeWindow = [];
  _currentActivity = 'unknown';

  // Reset pedometer tracking
  _currentStepCount = 0;
  _snapshotStepCount = 0;
  _snapshotTimestamp = 0;
  _stepsIncreasing = false;

  console.log('activity.monitoring_stopped');
}

/**
 * Get the most recently classified activity type.
 *
 * Returns "unknown" if monitoring hasn't started, the accelerometer
 * is unavailable, or the sliding window isn't full yet.
 */
export function getCurrentActivity(): ActivityType {
  return _currentActivity;
}
