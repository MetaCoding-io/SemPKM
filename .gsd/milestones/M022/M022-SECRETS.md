# Secrets Manifest

**Milestone:** 
**Generated:** 

### ASANA_CLIENT_ID

**Service:** 
**Status:** collected
**Destination:** dotenv

1. Navigate to https://app.asana.com/0/my-apps
2. Click "Create new app" (or select existing app)
3. Fill in app name (e.g. "SemPKM Sync") and redirect URL (`http://localhost:3000/app/asana-sync/_fragments/oauth-callback`)
4. Copy the "Client ID" from the app details page

### ASANA_CLIENT_SECRET

**Service:** 
**Status:** collected
**Destination:** dotenv

1. Navigate to https://app.asana.com/0/my-apps
2. Select the app created above
3. Click "Client secret" → "Show secret"
4. Copy the secret value
