import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

/**
 * Placeholder index screen for the authenticated app area.
 * T04 will replace this with the full tab navigator and dashboard.
 */
export default function AppIndex() {
  return (
    <View style={styles.container}>
      <Text style={styles.text}>Dashboard — coming in T04</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontSize: 16,
    color: '#666',
  },
});
