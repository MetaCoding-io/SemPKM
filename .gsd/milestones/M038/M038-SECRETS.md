# Secrets Manifest

**Milestone:** M038
**Generated:** 2026-03-23

### YOUTUBE_API_KEY

**Service:** YouTube Data API v3
**Dashboard:** https://console.cloud.google.com/apis/credentials
**Format hint:** `AIza...` (39-character string starting with `AIza`)
**Status:** collected
**Destination:** dotenv

1. Navigate to https://console.cloud.google.com/
2. Select or create a project (e.g. "SemPKM Media Scheduler")
3. Go to APIs & Services → Library → search "YouTube Data API v3" → Enable
4. Go to APIs & Services → Credentials → Create Credentials → API key
5. Optionally restrict the key to YouTube Data API v3 only
6. Copy the API key

### SPOTIFY_CLIENT_ID

**Service:** Spotify Web API
**Dashboard:** https://developer.spotify.com/dashboard
**Format hint:** 32-character hex string (e.g. `a1b2c3d4e5f6...`)
**Status:** collected
**Destination:** dotenv

1. Navigate to https://developer.spotify.com/dashboard
2. Log in with a Spotify account (free or Premium)
3. Click "Create App"
4. Set App name: "SemPKM Media Scheduler"
5. Set Redirect URI: `http://localhost:3000/app/media-scheduler/_fragments/oauth-callback`
6. Select "Web API" as the API to use
7. Save the app
8. Copy the Client ID from the app's settings page

### SPOTIFY_CLIENT_SECRET

**Service:** Spotify Web API
**Dashboard:** https://developer.spotify.com/dashboard
**Format hint:** 32-character hex string (e.g. `f6e5d4c3b2a1...`)
**Status:** collected
**Destination:** dotenv

1. Navigate to https://developer.spotify.com/dashboard
2. Open the "SemPKM Media Scheduler" app created above
3. Click "Settings" → "View client secret"
4. Copy the Client Secret
