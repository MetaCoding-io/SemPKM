import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { Redirect, Slot } from 'expo-router';

import { useSession } from '@/ctx';

/**
 * Authenticated route guard.
 *
 * - While the secure-store read is in progress, show a loading indicator.
 * - If no session exists, redirect to the sign-in screen.
 * - Otherwise, render the child route (tabs layout).
 */
export default function AppLayout() {
  const { session, isLoading } = useSession();

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
