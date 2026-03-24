import React from 'react';
import { Slot } from 'expo-router';

// Side-effect import: registers the geofencing background task at module
// scope so the OS can find the handler even if the app was killed.
// Must be imported before the app renders.
import '@/services/geofencing';

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
