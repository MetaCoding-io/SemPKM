import React from 'react';
import { Slot } from 'expo-router';

import { SessionProvider } from '@/ctx';

/**
 * Root layout — wraps the entire app in the auth SessionProvider.
 *
 * expo-router's <Slot> renders the matched child route.
 * All routes beneath this layout have access to useSession().
 */
export default function RootLayout() {
  return (
    <SessionProvider>
      <Slot />
    </SessionProvider>
  );
}
