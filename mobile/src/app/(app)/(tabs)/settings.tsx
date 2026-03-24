import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Pressable, StyleSheet, Switch, Text, View } from 'react-native';
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';

import { useSession, parseSession } from '@/ctx';
import { SemPKMClient } from '@/api/client';
import type { NotificationPreferences, TestNotificationResponse } from '@/api/client';
import { registerForPushNotifications } from '@/services/notifications';

/**
 * Settings screen showing connection info, notification prefs, and sign-out.
 */
export default function SettingsScreen() {
  const { session, signOut } = useSession();
  const creds = parseSession(session);

  const appVersion =
    Constants.expoConfig?.version ?? Constants.manifest2?.extra?.expoClient?.version ?? '1.0.0';

  // ── Notification state ──────────────────────────────────────

  const [permissionStatus, setPermissionStatus] = useState<string>('undetermined');
  const [notifEnabled, setNotifEnabled] = useState(false);
  const [isPhysicalDevice] = useState(Device.isDevice);
  const [sendingTest, setSendingTest] = useState(false);

  // Build client once from session
  const client = creds ? new SemPKMClient(creds.instanceUrl, creds.apiKey) : null;

  // Load permission status and preferences on mount
  useEffect(() => {
    let mounted = true;

    async function loadNotificationState() {
      try {
        // Check OS-level permission
        const perm = await Notifications.getPermissionsAsync();
        if (mounted) setPermissionStatus(perm.status);

        // Load server-side preferences
        if (client) {
          const prefs = await client.getNotificationPreferences();
          if (mounted) setNotifEnabled(prefs.enabled);
        }
      } catch (err) {
        console.error('settings.notification_load_error', {
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }

    loadNotificationState();
    return () => { mounted = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Handlers ────────────────────────────────────────────────

  const handleRequestPermission = useCallback(async () => {
    if (!client) return;

    try {
      const result = await Notifications.requestPermissionsAsync();
      setPermissionStatus(result.status);

      if (result.status === 'granted') {
        // Permission just granted — register the token
        await registerForPushNotifications(client);
      }
    } catch (err) {
      Alert.alert('Error', 'Failed to request notification permission.');
    }
  }, [client]);

  const handleToggleEnabled = useCallback(async (value: boolean) => {
    if (!client) return;

    setNotifEnabled(value);
    try {
      await client.updateNotificationPreferences({ enabled: value });
    } catch (err) {
      // Revert on failure
      setNotifEnabled(!value);
      Alert.alert('Error', 'Failed to update notification preferences.');
    }
  }, [client]);

  const handleSendTest = useCallback(async () => {
    if (!client) return;

    setSendingTest(true);
    try {
      const result: TestNotificationResponse = await client.sendTestNotification();
      if (result.suppressed) {
        Alert.alert(
          'Test Suppressed',
          `Notification was suppressed: ${result.reason ?? 'unknown reason'}`,
        );
      } else {
        Alert.alert(
          'Test Sent',
          `Sent to ${result.sent_count} device(s).`,
        );
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      Alert.alert('Error', `Failed to send test notification: ${message}`);
    } finally {
      setSendingTest(false);
    }
  }, [client]);

  const handleSignOut = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: () => signOut(),
      },
    ]);
  };

  // ── Permission status display ───────────────────────────────

  function permissionLabel(): string {
    switch (permissionStatus) {
      case 'granted': return 'Granted';
      case 'denied': return 'Denied';
      default: return 'Not Determined';
    }
  }

  function permissionColor(): string {
    switch (permissionStatus) {
      case 'granted': return '#059669';
      case 'denied': return '#dc2626';
      default: return '#d97706';
    }
  }

  // ── Render ──────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      {/* Connection info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connection</Text>
        <View style={styles.card}>
          <Text style={styles.cardLabel}>Connected to</Text>
          <Text style={styles.cardValue} numberOfLines={2}>
            {creds?.instanceUrl ?? 'Unknown'}
          </Text>
        </View>
      </View>

      {/* Push Notifications */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Push Notifications</Text>
        <View style={styles.card}>
          {!isPhysicalDevice ? (
            <Text style={styles.simulatorWarning}>
              Push notifications are not available on simulators.
            </Text>
          ) : (
            <>
              {/* Permission status */}
              <View style={styles.row}>
                <Text style={styles.cardLabel}>Permission</Text>
                <Text style={[styles.statusBadge, { color: permissionColor() }]}>
                  {permissionLabel()}
                </Text>
              </View>

              {/* Request permission button */}
              {permissionStatus !== 'granted' && (
                <Pressable
                  style={({ pressed }) => [
                    styles.actionButton,
                    pressed && styles.actionButtonPressed,
                  ]}
                  onPress={handleRequestPermission}
                >
                  <Text style={styles.actionButtonText}>Request Permission</Text>
                </Pressable>
              )}

              {/* Enable toggle */}
              {permissionStatus === 'granted' && (
                <>
                  <View style={[styles.row, styles.toggleRow]}>
                    <Text style={styles.cardValue}>Enable Notifications</Text>
                    <Switch
                      value={notifEnabled}
                      onValueChange={handleToggleEnabled}
                      trackColor={{ false: '#d1d5db', true: '#93c5fd' }}
                      thumbColor={notifEnabled ? '#208AEF' : '#f4f3f4'}
                    />
                  </View>

                  {/* Send test */}
                  <Pressable
                    style={({ pressed }) => [
                      styles.actionButton,
                      styles.testButton,
                      pressed && styles.actionButtonPressed,
                      sendingTest && styles.actionButtonDisabled,
                    ]}
                    onPress={handleSendTest}
                    disabled={sendingTest}
                  >
                    <Text style={styles.actionButtonText}>
                      {sendingTest ? 'Sending...' : 'Send Test Notification'}
                    </Text>
                  </Pressable>
                </>
              )}
            </>
          )}
        </View>
      </View>

      {/* App info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.card}>
          <Text style={styles.cardLabel}>App Version</Text>
          <Text style={styles.cardValue}>{appVersion}</Text>
        </View>
      </View>

      {/* Sign out */}
      <View style={styles.signOutSection}>
        <Pressable
          style={({ pressed }) => [
            styles.signOutButton,
            pressed && styles.signOutButtonPressed,
          ]}
          onPress={handleSignOut}
        >
          <Text style={styles.signOutText}>Sign Out</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
    paddingTop: 16,
  },

  // Section grouping
  section: {
    marginBottom: 24,
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 16,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#e5e7eb',
  },
  cardLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6b7280',
    marginBottom: 4,
  },
  cardValue: {
    fontSize: 16,
    color: '#111827',
  },

  // Row layout for inline label + value
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  toggleRow: {
    marginTop: 12,
    marginBottom: 12,
  },
  statusBadge: {
    fontSize: 13,
    fontWeight: '700',
  },

  // Simulator warning
  simulatorWarning: {
    fontSize: 14,
    color: '#9ca3af',
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 8,
  },

  // Action buttons
  actionButton: {
    backgroundColor: '#eff6ff',
    borderWidth: 1,
    borderColor: '#bfdbfe',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  actionButtonPressed: {
    backgroundColor: '#dbeafe',
  },
  actionButtonDisabled: {
    opacity: 0.5,
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1d4ed8',
  },
  testButton: {
    marginTop: 4,
  },

  // Sign out
  signOutSection: {
    marginTop: 'auto' as unknown as number,
    paddingHorizontal: 16,
    paddingBottom: 40,
  },
  signOutButton: {
    backgroundColor: '#fef2f2',
    borderWidth: 1,
    borderColor: '#fca5a5',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  signOutButtonPressed: {
    backgroundColor: '#fee2e2',
  },
  signOutText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#dc2626',
  },
});
