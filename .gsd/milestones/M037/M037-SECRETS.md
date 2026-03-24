# Secrets Manifest

**Milestone:** M037 — User Context & Mobile App
**Generated:** 2026-03-23

### FIREBASE_SERVICE_ACCOUNT_JSON

**Service:** Google Firebase (Cloud Messaging)
**Dashboard:** https://console.firebase.google.com/project/_/settings/serviceaccounts/adminsdk
**Format hint:** JSON file containing `type`, `project_id`, `private_key_id`, `private_key`, `client_email`, etc.
**Status:** collected
**Destination:** dotenv

1. Go to [Firebase Console](https://console.firebase.google.com/) and create a new project (or select existing)
2. Navigate to Project Settings → Service Accounts tab
3. Click "Generate new private key" → "Generate key"
4. Save the downloaded JSON file as `firebase-service-account.json` in the project root
5. Set `FIREBASE_SERVICE_ACCOUNT_JSON` in `.env` to the file path: `./firebase-service-account.json`
6. Alternatively, set the env var to the raw JSON string (base64-encoded) if preferred for Docker secrets

### FIREBASE_PROJECT_ID

**Service:** Google Firebase
**Dashboard:** https://console.firebase.google.com/project/_/settings/general
**Format hint:** lowercase string with hyphens, e.g. `sempkm-12345`
**Status:** collected
**Destination:** dotenv

1. Go to [Firebase Console](https://console.firebase.google.com/) → Project Settings → General tab
2. Copy the "Project ID" value
3. This is the same project used for the service account above
