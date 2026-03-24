import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Ionicons from '@expo/vector-icons/Ionicons';

/**
 * Placeholder screen for zone management.
 * Replaced in S04 with geofence zone configuration.
 */
export default function ZonesScreen() {
  return (
    <View style={styles.container}>
      <Ionicons name="location-outline" size={48} color="#9ca3af" />
      <Text style={styles.heading}>Zone Management</Text>
      <Text style={styles.subtext}>
        Coming in a future update. You'll be able to define geofence zones here.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    backgroundColor: '#f9fafb',
  },
  heading: {
    fontSize: 20,
    fontWeight: '600',
    color: '#374151',
    marginTop: 16,
    marginBottom: 8,
  },
  subtext: {
    fontSize: 14,
    color: '#6b7280',
    textAlign: 'center',
    maxWidth: 260,
  },
});
