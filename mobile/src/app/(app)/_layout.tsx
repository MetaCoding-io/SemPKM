import React, { useEffect } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Redirect, Slot } from 'expo-router';

import { useSession, parseSession } from '@/ctx';
import { SemPKMClient } from '@/api/client';
import {
  registerForPushNotifications,
  setupNotificationHandler,
  setupAndroidChannel,
} from '@/services/notifications';

/**
 * Authenticated route guard.
 *
 * - While the secure-store read is in progress, show a loading indicator.
 * - If no session exists, redirect to the sign-in screen.
 * - Otherwise, render the child route (tabs layout).
 *
 * Also initialises push notification infrastructure on mount and
 * registers the device push token after authentication.
 */
export default function AppLayout() {
  const { session, isLoading } = useSession();

  // ── Notification infrastructure (runs once on mount) ────────

  useEffect(() => {
    setupNotificationHandler();
    // Fire-and-forget — channel creation is async but non-critical
    setupAndroidChannel().catch((err) => {
      console.error('notifications.android_channel_error', {
        error: err instanceof Error ? err.message : String(err),
      });
    });
  }, []);

  // ── Token registration (runs when session becomes available) ─

  useEffect(() => {
    if (!session) return;

    const creds = parseSession(session);
    if (!creds) return;

    const client = new SemPKMClient(creds.instanceUrl, creds.apiKey);

    // Fire-and-forget — push registration failure must not block the app
    registerForPushNotifications(client).catch((err) => {
      console.error('notifications.registration_error', {
        error: err instanceof Error ? err.message : String(err),
      });
    });
  }, [session]);

  // ── Route guard ─────────────────────────────────────────────

  if (isLoading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  if (!session) {
    return <Redirect href="/sign-in" />;
  }

  return <Slot />;
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
