import React from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
import Constants from 'expo-constants';

import { useSession, parseSession } from '@/ctx';

/**
 * Settings screen showing connection info and sign-out.
 */
export default function SettingsScreen() {
  const { session, signOut } = useSession();
  const creds = parseSession(session);

  const appVersion =
    Constants.expoConfig?.version ?? Constants.manifest2?.extra?.expoClient?.version ?? '1.0.0';

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
