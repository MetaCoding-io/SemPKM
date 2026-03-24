import React, { useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { router } from 'expo-router';

import { useSession } from '@/ctx';
import { SemPKMClient, SemPKMError } from '@/api/client';

/**
 * Onboarding / sign-in screen.
 *
 * Collects the SemPKM instance URL and API key, tests the connection
 * via GET /.well-known/sempkm, and stores credentials on success.
 *
 * Error states:
 *  - Invalid URL format (not http:// or https://)
 *  - Network unreachable (SemPKMError.status === 0)
 *  - 401 invalid key
 *  - Other server errors (displayed as-is)
 */
export default function SignInScreen() {
  const { signIn } = useSession();

  const [instanceUrl, setInstanceUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  const canConnect =
    instanceUrl.trim().length > 0 && apiKey.trim().length > 0 && !connecting;

  async function handleConnect() {
    setError(null);

    // Validate URL format
    const trimmedUrl = instanceUrl.trim();
    if (
      !trimmedUrl.startsWith('http://') &&
      !trimmedUrl.startsWith('https://')
    ) {
      setError('URL must start with http:// or https://');
      return;
    }

    setConnecting(true);
    try {
      const client = new SemPKMClient(trimmedUrl, apiKey.trim());
      await client.connect();

      // Connection successful — store credentials and navigate
      signIn(trimmedUrl, apiKey.trim());
      router.replace('/');
    } catch (err) {
      if (err instanceof SemPKMError) {
        if (err.status === 0) {
          setError(
            'Could not reach server. Check the URL and your network connection.',
          );
        } else if (err.status === 401) {
          setError('Invalid API key. Please check your credentials.');
        } else {
          setError(err.detail ?? `Server error (${err.status})`);
        }
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setConnecting(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.inner}>
        <Text style={styles.title}>SemPKM</Text>
        <Text style={styles.subtitle}>Connect to your instance</Text>

        <View style={styles.form}>
          <Text style={styles.label}>Instance URL</Text>
          <TextInput
            style={styles.input}
            value={instanceUrl}
            onChangeText={setInstanceUrl}
            placeholder="https://sempkm.example.com"
            placeholderTextColor="#999"
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            editable={!connecting}
            returnKeyType="next"
          />

          <Text style={styles.label}>API Key</Text>
          <TextInput
            style={styles.input}
            value={apiKey}
            onChangeText={setApiKey}
            placeholder="Enter your API key"
            placeholderTextColor="#999"
            secureTextEntry
            autoCapitalize="none"
            autoCorrect={false}
            editable={!connecting}
            returnKeyType="done"
            onSubmitEditing={canConnect ? handleConnect : undefined}
          />

          {error && <Text style={styles.error}>{error}</Text>}

          <Pressable
            style={[
              styles.button,
              !canConnect && styles.buttonDisabled,
            ]}
            onPress={handleConnect}
            disabled={!canConnect}
          >
            {connecting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Connect</Text>
            )}
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 24,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    textAlign: 'center',
    marginBottom: 4,
    color: '#1a1a1a',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    marginBottom: 32,
  },
  form: {
    gap: 12,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: -4,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    color: '#1a1a1a',
    backgroundColor: '#fafafa',
  },
  error: {
    color: '#d32f2f',
    fontSize: 14,
    textAlign: 'center',
    paddingVertical: 4,
  },
  button: {
    backgroundColor: '#2563eb',
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
  },
  buttonDisabled: {
    backgroundColor: '#93b4f5',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
