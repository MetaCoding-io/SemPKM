/**
 * "Now Playing" card for the mobile dashboard.
 *
 * Fetches the current media suggestion from the media-scheduler app
 * and renders a card with title, source info, time slot, playback status,
 * and a deep-link "Play" button that opens the native app (Spotify,
 * YouTube, or podcast player).
 *
 * Renders nothing when no suggestion exists or the status is "none".
 * Handles network errors gracefully — never crashes the dashboard.
 *
 * @module components/MediaSuggestion
 */

import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import * as Linking from 'expo-linking';

import { SemPKMClient, SemPKMError } from '@/api/client';
import type { MediaSuggestion } from '@/api/client';

// ── Helpers ─────────────────────────────────────────────────────

/** Source-type emoji mapping. */
function sourceEmoji(type: MediaSuggestion['source_type']): string {
  switch (type) {
    case 'podcast':
      return '🎙️';
    case 'youtube':
      return '🎬';
    case 'spotify':
      return '🎵';
    default:
      return '📻';
  }
}

/** Human-readable source type label. */
function sourceLabel(type: MediaSuggestion['source_type']): string {
  switch (type) {
    case 'podcast':
      return 'Podcast';
    case 'youtube':
      return 'YouTube';
    case 'spotify':
      return 'Spotify';
    default:
      return 'Media';
  }
}

/** Format seconds as "Xm" or "Xh Ym". */
function formatDuration(seconds: number | null): string | null {
  if (seconds == null || seconds <= 0) return null;
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

// ── Props ───────────────────────────────────────────────────────

interface MediaSuggestionCardProps {
  instanceUrl: string;
  apiKey: string;
}

// ── Component ───────────────────────────────────────────────────

export function MediaSuggestionCard({
  instanceUrl,
  apiKey,
}: MediaSuggestionCardProps) {
  const [suggestion, setSuggestion] = useState<MediaSuggestion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetch() {
      setLoading(true);
      setError(null);

      try {
        const client = new SemPKMClient(instanceUrl, apiKey);
        const result = await client.getMediaSuggestion();
        if (!cancelled) {
          setSuggestion(result);
        }
      } catch (err) {
        if (!cancelled) {
          // Log but don't crash — the dashboard should remain functional
          const msg =
            err instanceof SemPKMError
              ? `Media suggestion fetch failed: ${err.status} ${err.detail}`
              : 'Media suggestion fetch failed';
          console.warn(msg);
          setError(msg);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetch();
    return () => {
      cancelled = true;
    };
  }, [instanceUrl, apiKey]);

  // ── Loading ───────────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.loadingRow}>
        <ActivityIndicator size="small" color="#6b7280" />
      </View>
    );
  }

  // ── Empty / error / no-plan: render nothing ───────────────

  if (error || !suggestion || suggestion.status === 'none') {
    return null;
  }

  // ── Active suggestion card ────────────────────────────────

  const isNow = suggestion.status === 'now';
  const hasUrl = !!suggestion.enclosure_url;
  const duration = formatDuration(suggestion.duration_seconds);

  const handlePlay = async () => {
    if (!suggestion.enclosure_url) return;
    try {
      await Linking.openURL(suggestion.enclosure_url);
    } catch (err) {
      console.warn('Failed to open media URL:', err);
    }
  };

  return (
    <View style={styles.card}>
      {/* Status badge */}
      <View style={styles.headerRow}>
        <View style={[styles.statusBadge, isNow ? styles.badgeNow : styles.badgeNext]}>
          <Text style={styles.statusText}>
            {isNow ? '▶ Now playing' : '⏭ Up next'}
          </Text>
        </View>
        {duration && <Text style={styles.duration}>{duration}</Text>}
      </View>

      {/* Source line */}
      {suggestion.source_type && (
        <Text style={styles.sourceLine}>
          {sourceEmoji(suggestion.source_type)}{' '}
          {suggestion.source_title ?? sourceLabel(suggestion.source_type)}
        </Text>
      )}

      {/* Title */}
      <Text style={styles.title} numberOfLines={2}>
        {suggestion.title}
      </Text>

      {/* Time slot */}
      <Text style={styles.timeSlot}>
        {suggestion.slot_start} – {suggestion.slot_end}
      </Text>

      {/* Play button */}
      {hasUrl && (
        <Pressable
          style={({ pressed }) => [
            styles.playButton,
            pressed && styles.playButtonPressed,
          ]}
          onPress={handlePlay}
          accessibilityRole="button"
          accessibilityLabel={`Play ${suggestion.title}`}
        >
          <Text style={styles.playButtonText}>
            {sourceEmoji(suggestion.source_type)} Play in{' '}
            {sourceLabel(suggestion.source_type)}
          </Text>
        </Pressable>
      )}
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────────

const styles = StyleSheet.create({
  loadingRow: {
    alignItems: 'center',
    paddingVertical: 12,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 16,
    marginBottom: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#e5e7eb',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  statusBadge: {
    paddingVertical: 3,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  badgeNow: {
    backgroundColor: '#dcfce7',
  },
  badgeNext: {
    backgroundColor: '#dbeafe',
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
  },
  duration: {
    fontSize: 12,
    color: '#9ca3af',
  },
  sourceLine: {
    fontSize: 13,
    color: '#6b7280',
    marginBottom: 4,
  },
  title: {
    fontSize: 17,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  timeSlot: {
    fontSize: 14,
    color: '#6b7280',
    marginBottom: 12,
  },
  playButton: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  playButtonPressed: {
    backgroundColor: '#1d4ed8',
  },
  playButtonText: {
    color: '#fff',
    fontSize: 15,
    fontWeight: '600',
  },
});
