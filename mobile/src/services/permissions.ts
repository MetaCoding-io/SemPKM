/**
 * Location permission utilities for SemPKM mobile app.
 *
 * Implements the foreground-then-background permission request
 * sequence required by both iOS and Android for "always" location
 * access. Background permission can only be requested after
 * foreground has been granted.
 *
 * @module services/permissions
 */

import * as Location from 'expo-location';

// ── Types ───────────────────────────────────────────────────────

export interface LocationPermissionStatus {
  foreground: Location.PermissionStatus;
  background: Location.PermissionStatus;
}

// ── Permission functions ────────────────────────────────────────

/**
 * Request location permissions in the correct sequence:
 * 1. Check/request foreground permission
 * 2. If foreground granted, check/request background permission
 *
 * Returns the final status of both permission levels.
 *
 * iOS requires "When In Use" before "Always" can be requested.
 * Android 10+ requires foreground before background.
 */
export async function requestLocationPermissions(): Promise<LocationPermissionStatus> {
  // Step 1: Foreground permission
  let fgStatus = await Location.getForegroundPermissionsAsync();
  if (fgStatus.status !== Location.PermissionStatus.GRANTED) {
    fgStatus = await Location.requestForegroundPermissionsAsync();
  }

  // Step 2: Background permission (only if foreground was granted)
  let bgStatus = await Location.getBackgroundPermissionsAsync();
  if (
    fgStatus.status === Location.PermissionStatus.GRANTED &&
    bgStatus.status !== Location.PermissionStatus.GRANTED
  ) {
    bgStatus = await Location.requestBackgroundPermissionsAsync();
  }

  return {
    foreground: fgStatus.status,
    background: bgStatus.status,
  };
}

/**
 * Check whether both foreground and background location permissions
 * are granted. Returns true only when full "always" access is available.
 */
export async function hasFullLocationPermission(): Promise<boolean> {
  const fg = await Location.getForegroundPermissionsAsync();
  const bg = await Location.getBackgroundPermissionsAsync();
  return (
    fg.status === Location.PermissionStatus.GRANTED &&
    bg.status === Location.PermissionStatus.GRANTED
  );
}

/**
 * Get current permission status for both levels.
 * Useful for UI display (e.g. settings screen showing permission state).
 */
export async function getPermissionStatus(): Promise<LocationPermissionStatus> {
  const fg = await Location.getForegroundPermissionsAsync();
  const bg = await Location.getBackgroundPermissionsAsync();
  return {
    foreground: fg.status,
    background: bg.status,
  };
}
