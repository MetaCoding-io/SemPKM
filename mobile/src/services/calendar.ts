/**
 * Calendar service for SemPKM mobile context detection.
 *
 * Reads device calendar events to detect current/upcoming meetings,
 * extracting event title and busy status for automatic context updates.
 * Handles permission lifecycle and degrades gracefully when access
 * is denied or no calendars/events are available.
 *
 * Diagnostic keys (for Expo dev tools filtering):
 *   calendar.permission_granted   — read access approved
 *   calendar.permission_denied    — user declined calendar access
 *   calendar.no_calendars         — device has no readable calendars
 *   calendar.events_fetched       — successful event query (includes count)
 *   calendar.error                — unexpected failure in calendar API
 *
 * Privacy: Only event title and availability are read/transmitted.
 * Descriptions, attendees, and other PII are never accessed.
 *
 * @module services/calendar
 */

import * as Calendar from 'expo-calendar';
import { PermissionStatus } from 'expo-modules-core';

// ── Types ───────────────────────────────────────────────────────

export interface CalendarEventInfo {
  /** Title of the current/upcoming event, or null if none. */
  title: string | null;
  /** Whether the user is busy (true if event availability is 'busy' or unspecified). */
  busy: boolean;
}

// ── Module-level permission cache ───────────────────────────────

let _permissionGranted: boolean | null = null;

// ── Exported functions ──────────────────────────────────────────

/**
 * Request calendar read permission.
 *
 * Checks cached status first to avoid repeated OS prompts.
 * Returns true if permission was granted, false otherwise.
 */
export async function requestCalendarPermission(): Promise<boolean> {
  // Return cached result if we already have a definitive answer
  if (_permissionGranted !== null) {
    return _permissionGranted;
  }

  try {
    // Check existing status before prompting
    const existing = await Calendar.getCalendarPermissionsAsync();
    if (existing.status === PermissionStatus.GRANTED) {
      _permissionGranted = true;
      console.log('calendar.permission_granted', 'Already granted');
      return true;
    }

    // If already permanently denied, don't re-prompt
    if (existing.status === PermissionStatus.DENIED && !existing.canAskAgain) {
      _permissionGranted = false;
      console.log('calendar.permission_denied', 'Permanently denied — cannot re-prompt');
      return false;
    }

    // Request permission
    const result = await Calendar.requestCalendarPermissionsAsync();
    _permissionGranted = result.status === PermissionStatus.GRANTED;

    if (_permissionGranted) {
      console.log('calendar.permission_granted', 'User approved');
    } else {
      console.log('calendar.permission_denied', 'User declined');
    }

    return _permissionGranted;
  } catch (err) {
    console.error('calendar.error', {
      phase: 'permission_request',
      error: err instanceof Error ? err.message : String(err),
    });
    _permissionGranted = false;
    return false;
  }
}

/**
 * Get the current or upcoming calendar event within a 5-minute lookahead window.
 *
 * Returns `{ title: null, busy: false }` when:
 * - Calendar permission was not granted
 * - No calendars exist on the device
 * - No events fall within the current → now+5min window
 *
 * Busy status is true when the event's availability is 'busy' or unspecified
 * (many calendar providers omit availability, defaulting to busy semantics).
 */
export async function getCurrentCalendarEvent(): Promise<CalendarEventInfo> {
  const NO_EVENT: CalendarEventInfo = { title: null, busy: false };

  // Check permission (uses cache after first call)
  const hasPermission = await requestCalendarPermission();
  if (!hasPermission) {
    return NO_EVENT;
  }

  try {
    // Get all readable calendars
    const calendars = await Calendar.getCalendarsAsync(
      Calendar.EntityTypes.EVENT
    );

    if (calendars.length === 0) {
      console.log('calendar.no_calendars', 'No event calendars found on device');
      return NO_EVENT;
    }

    const calendarIds = calendars.map((c) => c.id);

    // Query events: now → now + 5 minutes
    const now = new Date();
    const fiveMinutesLater = new Date(now.getTime() + 5 * 60 * 1000);

    const events = await Calendar.getEventsAsync(
      calendarIds,
      now,
      fiveMinutesLater
    );

    console.log('calendar.events_fetched', { count: events.length });

    if (events.length === 0) {
      return NO_EVENT;
    }

    // Pick the best event: prefer one that's already started (current),
    // otherwise take the soonest upcoming event.
    const sorted = [...events].sort((a, b) => {
      const aStart = new Date(a.startDate).getTime();
      const bStart = new Date(b.startDate).getTime();
      return aStart - bStart;
    });

    // Find a current event (started before or at now)
    const nowMs = now.getTime();
    const currentEvent = sorted.find((e) => {
      const start = new Date(e.startDate).getTime();
      return start <= nowMs;
    });

    const event = currentEvent ?? sorted[0];

    // Extract title — handle empty/whitespace-only titles
    const title = event.title?.trim() || null;

    // Determine busy status:
    // - 'busy' → true
    // - 'free' → false
    // - 'tentative' → true (treat tentative as potentially busy)
    // - unspecified/null → true (conservative default)
    const busy = event.availability !== Calendar.Availability.FREE;

    return { title, busy };
  } catch (err) {
    console.error('calendar.error', {
      phase: 'get_events',
      error: err instanceof Error ? err.message : String(err),
    });
    return NO_EVENT;
  }
}

/**
 * Reset the cached permission state.
 * Useful when the user returns from OS settings where they may have
 * changed calendar permissions.
 */
export function resetPermissionCache(): void {
  _permissionGranted = null;
}
