/**
 * Push notification service for SemPKM mobile app.
 *
 * Handles permission requests, native FCM/APNs token retrieval,
 * backend registration, foreground notification display, and
 * Android channel setup.
 *
 * Uses native device push tokens (NOT Expo push tokens) per D338 —
 * the backend dispatches via firebase-admin directly.
 *
 * Diagnostic keys (for console filtering):
 *   notifications.permission_status    — current permission state
 *   notifications.token_registered     — token sent to backend (prefix only)
 *   notifications.handler_setup        — foreground handler configured
 *   notifications.channel_created      — Android notification channel ready
 *   notifications.registration_error   — token retrieval or registration failed
 *   notifications.not_physical_device  — running on simulator, skipped
 *
 * Privacy: FCM/APNs tokens are never logged in full — only first 20 chars.
 *
 * @module services/notifications
 */

import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';

import type { SemPKMClient } from '@/api/client';

// ── Token prefix for safe logging ───────────────────────────────

function tokenPrefix(token: string): string {
  return token.length > 20 ? token.substring(0, 20) + '...' : token;
}

// ── Permission + Registration ───────────────────────────────────

/**
 * Request notification permissions, retrieve the native push token,
 * and register it with the SemPKM backend.
 *
 * Skips silently on simulators (Device.isDevice check).
 * Skips silently if the user denies permission.
 * Logs errors but never throws — push registration failure must
 * not break app startup.
 */
export async function registerForPushNotifications(
  client: SemPKMClient,
): Promise<void> {
  // Simulators/emulators can't receive push notifications
  if (!Device.isDevice) {
    console.log('notifications.not_physical_device', 'Skipping push registration on simulator');
    return;
  }

  try {
    // Check existing permission
    let permStatus = await Notifications.getPermissionsAsync();
    console.log('notifications.permission_status', permStatus.status);

    if (permStatus.status !== 'granted') {
      // Request permission from the user
      permStatus = await Notifications.requestPermissionsAsync();
      console.log('notifications.permission_status', permStatus.status);
    }

    if (permStatus.status !== 'granted') {
      // User declined — nothing more we can do
      return;
    }

    // Get the native FCM (Android) or APNs (iOS) token
    // NOT getExpoPushTokenAsync — we use firebase-admin on the backend (D338)
    const tokenResponse = await Notifications.getDevicePushTokenAsync();
    const token = tokenResponse.data;

    // Register with backend
    await client.registerPushToken(
      token,
      Platform.OS,
      `${Device.modelName ?? Platform.OS} (${Device.osName} ${Device.osVersion})`,
    );

    console.log('notifications.token_registered', {
      platform: Platform.OS,
      tokenPrefix: tokenPrefix(token),
    });
  } catch (err) {
    // Push registration failure must never break the app
    console.error('notifications.registration_error', {
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

// ── Foreground notification handler ─────────────────────────────

/**
 * Configure how notifications are displayed when the app is in the foreground.
 *
 * By default, notifications received while the app is open are silently
 * swallowed. This handler makes them visible (alert + sound + badge).
 *
 * Also registers a listener for notification tap responses (for future
 * deep-linking in S07).
 */
export function setupNotificationHandler(): void {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    }),
  });

  // Tap-to-navigate listener — log for now, deep linking is S07 territory
  Notifications.addNotificationResponseReceivedListener((response) => {
    const data = response.notification.request.content.data;
    console.log('notifications.response_received', {
      actionId: response.actionIdentifier,
      data: data ?? {},
    });
  });

  console.log('notifications.handler_setup', 'Foreground notification display enabled');
}

// ── Android channel ─────────────────────────────────────────────

/**
 * Create the default Android notification channel.
 *
 * Android 8+ requires a channel for notifications to appear.
 * This is a no-op on iOS (the API call is guarded by platform check).
 */
export async function setupAndroidChannel(): Promise<void> {
  if (Platform.OS !== 'android') return;

  await Notifications.setNotificationChannelAsync('default', {
    name: 'Default',
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 250, 250, 250],
    lightColor: '#208AEF',
  });

  console.log('notifications.channel_created', 'Default Android channel configured');
}
