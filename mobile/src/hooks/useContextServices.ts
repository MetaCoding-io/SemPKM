/**
 * Context services orchestrator hook for SemPKM mobile.
 *
 * Coordinates three enrichment services — calendar, activity, and
 * time-period — into a single rate-limited context update stream.
 * Prevents the three services from each calling updateContext()
 * independently (which would hit the backend's 12/min rate limit).
 *
 * Behavior:
 *   - Activity monitoring starts on mount (continuous 1Hz via accelerometer)
 *   - Calendar is polled every 60 seconds
 *   - Time period is recomputed on each polling cycle
 *   - On app foreground (AppState 'active'), immediately re-polls calendar
 *     and recomputes time period
 *   - All values are compared against previous push — only calls
 *     updateContext() when at least one field has changed
 *   - Minimum 30-second gap between pushes (rate-limit protection)
 *   - All subscriptions and intervals cleaned up on unmount
 *
 * Diagnostic keys (for Expo dev tools filtering):
 *   context.update_sent         — batched update pushed to server
 *   context.update_skipped      — update skipped (no changes or rate-limited)
 *   context.api_error           — updateContext() network/API failure
 *   context.services_started    — orchestrator initialised
 *   context.services_stopped    — orchestrator cleaned up
 *   context.foreground_refresh  — app returned to foreground, re-polling
 *
 * @module hooks/useContextServices
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { AppState, type AppStateStatus } from 'react-native';

import { useSession, parseSession } from '@/ctx';
import { SemPKMClient } from '@/api/client';
import {
  requestCalendarPermission,
  getCurrentCalendarEvent,
  type CalendarEventInfo,
} from '@/services/calendar';
import {
  startActivityMonitoring,
  stopActivityMonitoring,
  getCurrentActivity,
  type ActivityType,
} from '@/services/activity';
import { getTimePeriod, type TimePeriod } from '@/services/time-period';

// ── Constants ───────────────────────────────────────────────────

/** Polling interval for calendar + time-period (ms). */
const POLL_INTERVAL_MS = 60_000;

/** Minimum gap between updateContext() calls (ms). */
const MIN_PUSH_GAP_MS = 30_000;

// ── Types ───────────────────────────────────────────────────────

export interface ContextServicesState {
  /** Current/upcoming calendar event title, or null. */
  calendarEvent: string | null;
  /** Whether the calendar shows the user as busy. */
  calendarBusy: boolean;
  /** Detected physical activity type. */
  activity: ActivityType;
  /** Current time-of-day period. */
  timePeriod: TimePeriod;
  /** Whether sensor monitoring is active. */
  isMonitoring: boolean;
}

/** Fields tracked for change detection. */
interface TrackedFields {
  calendarEvent: string | null;
  calendarBusy: boolean;
  activity: string;
  timePeriod: string;
}

// ── Hook ────────────────────────────────────────────────────────

/**
 * Orchestrator hook that coordinates calendar, activity, and time-period
 * services into batched, rate-limited context updates.
 */
export function useContextServices(): ContextServicesState {
  const { session } = useSession();

  // Current detected values (for rendering)
  const [calendarEvent, setCalendarEvent] = useState<string | null>(null);
  const [calendarBusy, setCalendarBusy] = useState(false);
  const [activity, setActivity] = useState<ActivityType>('unknown');
  const [timePeriod, setTimePeriod] = useState<TimePeriod>(getTimePeriod());
  const [isMonitoring, setIsMonitoring] = useState(false);

  // Refs for change tracking and rate limiting
  const lastPushedRef = useRef<TrackedFields | null>(null);
  const lastPushTimeRef = useRef(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  /**
   * Build a SemPKMClient from the current session.
   * Returns null if session is missing/invalid.
   */
  const getClient = useCallback((): SemPKMClient | null => {
    const creds = parseSession(session);
    if (!creds) return null;
    return new SemPKMClient(creds.instanceUrl, creds.apiKey);
  }, [session]);

  /**
   * Push a context update if any field changed and rate limit permits.
   */
  const maybePushUpdate = useCallback(
    async (fields: TrackedFields) => {
      // Change detection — compare each field with last pushed values
      const prev = lastPushedRef.current;
      if (prev !== null) {
        const unchanged =
          fields.calendarEvent === prev.calendarEvent &&
          fields.calendarBusy === prev.calendarBusy &&
          fields.activity === prev.activity &&
          fields.timePeriod === prev.timePeriod;

        if (unchanged) {
          console.log('context.update_skipped', { reason: 'no_changes' });
          return;
        }
      }

      // Rate limit — minimum 30s between pushes
      const now = Date.now();
      if (now - lastPushTimeRef.current < MIN_PUSH_GAP_MS) {
        console.log('context.update_skipped', {
          reason: 'rate_limited',
          nextAllowedIn: Math.ceil(
            (MIN_PUSH_GAP_MS - (now - lastPushTimeRef.current)) / 1000,
          ),
        });
        return;
      }

      const client = getClient();
      if (!client) {
        console.log('context.update_skipped', { reason: 'no_session' });
        return;
      }

      try {
        await client.updateContext({
          calendar_event: fields.calendarEvent,
          calendar_busy: fields.calendarBusy,
          activity: fields.activity,
          time_period: fields.timePeriod,
        });

        lastPushedRef.current = { ...fields };
        lastPushTimeRef.current = Date.now();

        console.log('context.update_sent', {
          calendarEvent: fields.calendarEvent,
          calendarBusy: fields.calendarBusy,
          activity: fields.activity,
          timePeriod: fields.timePeriod,
        });
      } catch (err) {
        const status = (err as { status?: number }).status ?? 0;
        const message =
          err instanceof Error ? err.message : String(err);
        console.error('context.api_error', { status, message });
      }
    },
    [getClient],
  );

  /**
   * Poll all services and attempt a batched push.
   */
  const pollAndPush = useCallback(async () => {
    if (!mountedRef.current) return;

    // Calendar: async query
    const calInfo: CalendarEventInfo = await getCurrentCalendarEvent();

    // Activity: synchronous read of latest classification
    const act: ActivityType = getCurrentActivity();

    // Time period: synchronous computation
    const tp: TimePeriod = getTimePeriod();

    if (!mountedRef.current) return;

    // Update React state for rendering
    setCalendarEvent(calInfo.title);
    setCalendarBusy(calInfo.busy);
    setActivity(act);
    setTimePeriod(tp);

    // Attempt batched push
    await maybePushUpdate({
      calendarEvent: calInfo.title,
      calendarBusy: calInfo.busy,
      activity: act,
      timePeriod: tp,
    });
  }, [maybePushUpdate]);

  // ── Lifecycle effect ────────────────────────────────────────

  useEffect(() => {
    mountedRef.current = true;
    let appStateSubscription: ReturnType<typeof AppState.addEventListener> | null = null;

    async function init() {
      // Request calendar permission (one-time OS prompt)
      await requestCalendarPermission();

      // Start continuous activity monitoring
      await startActivityMonitoring();
      if (!mountedRef.current) return;
      setIsMonitoring(true);

      // Initial poll
      await pollAndPush();

      // Set up periodic polling
      intervalRef.current = setInterval(() => {
        pollAndPush();
      }, POLL_INTERVAL_MS);

      // Listen for app foreground to refresh immediately
      appStateSubscription = AppState.addEventListener(
        'change',
        (nextState: AppStateStatus) => {
          if (nextState === 'active') {
            console.log('context.foreground_refresh');
            pollAndPush();
          }
        },
      );

      console.log('context.services_started', {
        pollIntervalMs: POLL_INTERVAL_MS,
        minPushGapMs: MIN_PUSH_GAP_MS,
      });
    }

    init();

    // Cleanup
    return () => {
      mountedRef.current = false;

      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }

      if (appStateSubscription !== null) {
        appStateSubscription.remove();
        appStateSubscription = null;
      }

      stopActivityMonitoring();
      setIsMonitoring(false);

      console.log('context.services_stopped');
    };
  }, [pollAndPush]);

  return {
    calendarEvent,
    calendarBusy,
    activity,
    timePeriod,
    isMonitoring,
  };
}
