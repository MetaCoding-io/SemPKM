/**
 * Time-of-day classification service for SemPKM mobile context detection.
 *
 * Classifies the current local time into one of four periods:
 *   morning     — 05:00 – 08:59
 *   work_hours  — 09:00 – 16:59
 *   evening     — 17:00 – 20:59
 *   night       — 21:00 – 04:59
 *
 * Uses the device's local timezone via Date.getHours(). All 24 hours
 * are covered with no gaps.
 *
 * Diagnostic keys (for Expo dev tools filtering):
 *   timePeriod.classified — current classification with hour
 *
 * @module services/time-period
 */

// ── Types ───────────────────────────────────────────────────────

export type TimePeriod = 'morning' | 'work_hours' | 'evening' | 'night';

// ── Exported functions ──────────────────────────────────────────

/**
 * Classify a date/time into a time-of-day period.
 *
 * @param date - Date to classify. Defaults to current time.
 * @returns One of: morning, work_hours, evening, night.
 *
 * Hour boundaries (local time, inclusive):
 *   05–08 → morning
 *   09–16 → work_hours
 *   17–20 → evening
 *   21–04 → night
 */
export function getTimePeriod(date?: Date): TimePeriod {
  const hour = (date ?? new Date()).getHours();

  if (hour >= 5 && hour <= 8) {
    return 'morning';
  }
  if (hour >= 9 && hour <= 16) {
    return 'work_hours';
  }
  if (hour >= 17 && hour <= 20) {
    return 'evening';
  }
  // hour >= 21 || hour <= 4
  return 'night';
}
