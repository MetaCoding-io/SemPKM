/**
 * Geofencing background task for SemPKM mobile app.
 *
 * CRITICAL: TaskManager.defineTask() is called at module top-level scope.
 * This module must be imported in the root _layout.tsx via a side-effect
 * import (`import '@/services/geofencing'`) BEFORE the app renders, so
 * the OS can locate the task handler even when the app was killed.
 *
 * The task callback runs outside the React component tree — no hooks, no
 * context providers. Credentials are read directly from expo-secure-store.
 *
 * @module services/geofencing
 */

import * as TaskManager from 'expo-task-manager';
import * as Location from 'expo-location';
import * as SecureStore from 'expo-secure-store';

// ── Constants ───────────────────────────────────────────────────

export const GEOFENCE_TASK = 'sempkm-geofence-task';

// ── Zone type (lightweight — avoids importing from api/client) ──

export interface GeofenceZone {
  name: string;
  latitude: number;
  longitude: number;
  radius_meters: number;
  enabled: boolean;
}

// ── Background task definition (MODULE SCOPE) ───────────────────

TaskManager.defineTask(GEOFENCE_TASK, async ({ data, error }) => {
  if (error) {
    console.error('geofence.task_error', error);
    return;
  }

  const { eventType, region } = data as {
    eventType: Location.GeofencingEventType;
    region: Location.LocationRegion;
  };

  console.log('geofence.transition', {
    event: eventType === Location.GeofencingEventType.Enter ? 'enter' : 'exit',
    region: region.identifier,
  });

  // Read credentials from secure store (no React context available)
  const raw = await SecureStore.getItemAsync('session');
  if (!raw) {
    console.warn('geofence.no_session', 'No stored session — skipping context update');
    return;
  }

  let instanceUrl: string;
  let apiKey: string;
  try {
    const parsed = JSON.parse(raw);
    instanceUrl = parsed.instanceUrl;
    apiKey = parsed.apiKey;
    if (!instanceUrl || !apiKey) {
      console.warn('geofence.invalid_session', 'Session missing instanceUrl or apiKey');
      return;
    }
  } catch {
    console.error('geofence.session_parse_error', 'Failed to parse session JSON');
    return;
  }

  // On enter → set zone name; on exit → clear zone
  const zoneName =
    eventType === Location.GeofencingEventType.Enter ? region.identifier : null;

  try {
    const url = `${instanceUrl.replace(/\/+$/, '')}/api/context/update`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ location_zone: zoneName }),
    });

    if (!response.ok) {
      console.error('geofence.api_error', {
        status: response.status,
        zone: region.identifier,
      });
    }
  } catch (err) {
    console.error('geofence.network_error', {
      error: err instanceof Error ? err.message : String(err),
      zone: region.identifier,
    });
  }
});

// ── Exported functions ──────────────────────────────────────────

/**
 * Register geofence regions for all enabled zones.
 *
 * Maps zones to the Location.LocationRegion shape expected by
 * startGeofencingAsync. Skips disabled zones. If no zones are
 * enabled, stops geofencing instead.
 */
export async function registerGeofences(zones: GeofenceZone[]): Promise<void> {
  const enabledZones = zones.filter((z) => z.enabled);

  if (enabledZones.length === 0) {
    await stopGeofencing();
    return;
  }

  const regions: Location.LocationRegion[] = enabledZones.map((z) => ({
    identifier: z.name,
    latitude: z.latitude,
    longitude: z.longitude,
    radius: z.radius_meters,
    notifyOnEnter: true,
    notifyOnExit: true,
  }));

  await Location.startGeofencingAsync(GEOFENCE_TASK, regions);
  console.log('geofence.registered', { count: regions.length });
}

/**
 * Stop all geofencing monitoring.
 */
export async function stopGeofencing(): Promise<void> {
  const active = await isGeofencingActive();
  if (active) {
    await Location.stopGeofencingAsync(GEOFENCE_TASK);
    console.log('geofence.stopped');
  }
}

/**
 * Check whether geofencing is currently active.
 */
export async function isGeofencingActive(): Promise<boolean> {
  return Location.hasStartedGeofencingAsync(GEOFENCE_TASK);
}
