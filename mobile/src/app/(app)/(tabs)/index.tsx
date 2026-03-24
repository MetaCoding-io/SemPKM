import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { useSession, parseSession } from '@/ctx';
import { SemPKMClient, SemPKMError } from '@/api/client';
import type { ContextResponse } from '@/api/client';

// ── Helpers ─────────────────────────────────────────────────────

/**
 * Format an ISO-8601 timestamp as a human-readable relative string.
 * Returns "just now", "Xm ago", "Xh ago", or the date for >24h.
 */
function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 'Unknown';

  const diffMs = Date.now() - then;
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;

  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;

  return new Date(iso).toLocaleDateString();
}

// ── Component ───────────────────────────────────────────────────

export default function DashboardScreen() {
  const { session } = useSession();

  const [context, setContext] = useState<ContextResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchContext = useCallback(
    async (isRefresh = false) => {
      const creds = parseSession(session);
      if (!creds) return;

      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const client = new SemPKMClient(creds.instanceUrl, creds.apiKey);
        const result = await client.getCurrentContext();
        setContext(result);
      } catch (err) {
        if (err instanceof SemPKMError) {
          setError(
            err.status === 0
              ? 'Could not reach server. Check your connection.'
              : `Server error: ${err.detail ?? err.message}`,
          );
        } else {
          setError('An unexpected error occurred.');
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [session],
  );

  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  // ── Loading state ───────────────────────────────────────────

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  // ── Error state ─────────────────────────────────────────────

  if (error && !context) {
    return (
      <ScrollView
        contentContainerStyle={styles.centered}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => fetchContext(true)} />
        }
      >
        <Text style={styles.errorText}>{error}</Text>
        <Pressable style={styles.retryButton} onPress={() => fetchContext()}>
          <Text style={styles.retryButtonText}>Retry</Text>
        </Pressable>
      </ScrollView>
    );
  }

  // ── Empty state ─────────────────────────────────────────────

  if (!context) {
    return (
      <ScrollView
        contentContainerStyle={styles.centered}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => fetchContext(true)} />
        }
      >
        <Text style={styles.emptyTitle}>No context data yet</Text>
        <Text style={styles.emptySubtext}>
          Context updates will appear here when sent from this device.
        </Text>
      </ScrollView>
    );
  }

  // ── Context display ─────────────────────────────────────────

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => fetchContext(true)} />
      }
    >
      {/* Staleness banner */}
      <View style={styles.stalenessRow}>
        <View
          style={[
            styles.stalenessIndicator,
            context.is_stale ? styles.staleRed : styles.staleFresh,
          ]}
        />
        <Text style={styles.stalenessText}>
          {context.is_stale ? 'Stale' : 'Fresh'}
          {' · '}
          Last updated: {relativeTime(context.updated_at)}
        </Text>
      </View>

      {/* Context fields */}
      <ContextField label="Location" value={context.location_zone ?? 'Not set'} />
      <ContextField label="Activity" value={context.activity ?? 'Not set'} />
      <ContextField label="Time Period" value={context.time_period ?? 'Not set'} />
      <ContextField label="Calendar" value={context.calendar_event ?? 'None'} />

      {/* Inline error for refresh failures */}
      {error ? <Text style={styles.inlineError}>{error}</Text> : null}
    </ScrollView>
  );
}

// ── Field component ─────────────────────────────────────────────

function ContextField({ label, value }: { label: string; value: string }) {
  const isSet = value !== 'Not set' && value !== 'None';
  return (
    <View style={styles.fieldCard}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <Text style={[styles.fieldValue, !isSet && styles.fieldValueMuted]}>
        {value}
      </Text>
    </View>
  );
}

// ── Styles ──────────────────────────────────────────────────────

const styles = StyleSheet.create({
  centered: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },

  // Staleness
  stalenessRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#fff',
    borderRadius: 10,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#e5e7eb',
  },
  stalenessIndicator: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 8,
  },
  staleFresh: {
    backgroundColor: '#22c55e',
  },
  staleRed: {
    backgroundColor: '#ef4444',
  },
  stalenessText: {
    fontSize: 14,
    color: '#374151',
  },

  // Field cards
  fieldCard: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 16,
    marginBottom: 12,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#e5e7eb',
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  fieldValue: {
    fontSize: 17,
    color: '#111827',
  },
  fieldValueMuted: {
    color: '#9ca3af',
  },

  // Error state
  errorText: {
    fontSize: 16,
    color: '#ef4444',
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    paddingVertical: 10,
    paddingHorizontal: 24,
    backgroundColor: '#2563eb',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  inlineError: {
    fontSize: 14,
    color: '#ef4444',
    textAlign: 'center',
    marginTop: 8,
  },

  // Empty state
  emptyTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtext: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    maxWidth: 280,
  },
});
