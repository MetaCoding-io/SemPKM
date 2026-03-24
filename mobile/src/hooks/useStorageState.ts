/**
 * React hook that syncs a single string value between React state
 * and expo-secure-store (or localStorage on web).
 *
 * Follows the Expo docs recommended pattern:
 *   useReducer for [isLoading, value], useEffect for initial load,
 *   useCallback for the setter.
 *
 * @module hooks/useStorageState
 */

import { useCallback, useEffect, useReducer } from 'react';
import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

// ── State shape ─────────────────────────────────────────────────

type StorageState = [boolean, string | null]; // [isLoading, value]

type StorageAction =
  | { type: 'loaded'; value: string | null }
  | { type: 'set'; value: string | null };

function reducer(_state: StorageState, action: StorageAction): StorageState {
  switch (action.type) {
    case 'loaded':
      return [false, action.value];
    case 'set':
      return [false, action.value];
  }
}

// ── Storage abstraction ─────────────────────────────────────────

function useAsyncStorage(key: string) {
  // On web, fall back to localStorage (SecureStore is native-only)
  const isWeb = Platform.OS === 'web';

  const getItem = useCallback(async (): Promise<string | null> => {
    if (isWeb) {
      try {
        return localStorage.getItem(key);
      } catch {
        return null;
      }
    }
    return SecureStore.getItemAsync(key);
  }, [key, isWeb]);

  const setItem = useCallback(
    async (value: string | null): Promise<void> => {
      if (isWeb) {
        try {
          if (value === null) {
            localStorage.removeItem(key);
          } else {
            localStorage.setItem(key, value);
          }
        } catch {
          // localStorage may be blocked in some contexts
        }
        return;
      }
      if (value === null) {
        await SecureStore.deleteItemAsync(key);
      } else {
        await SecureStore.setItemAsync(key, value);
      }
    },
    [key, isWeb],
  );

  return { getItem, setItem };
}

// ── Public hook ─────────────────────────────────────────────────

/**
 * Persist and read a string value in secure storage.
 *
 * @param key - Storage key (e.g. "session")
 * @returns A tuple: [[isLoading, value], setValue]
 *
 * @example
 * const [[isLoading, session], setSession] = useStorageState('session');
 * setSession(JSON.stringify({ instanceUrl, apiKey }));
 * setSession(null); // clears
 */
export function useStorageState(
  key: string,
): [StorageState, (value: string | null) => void] {
  const [[isLoading, storedValue], dispatch] = useReducer(reducer, [
    true,
    null,
  ] as StorageState);

  const { getItem, setItem } = useAsyncStorage(key);

  // Load the persisted value on mount
  useEffect(() => {
    getItem().then((value) => {
      dispatch({ type: 'loaded', value });
    });
  }, [getItem]);

  // Setter: update React state and persist
  const setValue = useCallback(
    (value: string | null) => {
      dispatch({ type: 'set', value });
      setItem(value);
    },
    [setItem],
  );

  return [[isLoading, storedValue], setValue];
}
