# Secrets Manifest

**Milestone:** 
**Generated:** 

### GOOGLE_CLIENT_ID

**Service:** 
**Status:** skipped
**Destination:** dotenv

1. Go to https://console.cloud.google.com/
2. Select or create a project
3. Navigate to APIs & Services → Credentials
4. Click "Create Credentials" → "OAuth client ID"
5. Select "Web application" as Application type
6. Add `http://localhost:3000/app/google-calendar/_fragments/oauth-callback` to Authorized redirect URIs
7. Copy the Client ID

### GOOGLE_CLIENT_SECRET

**Service:** 
**Status:** skipped
**Destination:** dotenv

1. Same credentials page as GOOGLE_CLIENT_ID
2. Copy the Client secret from the OAuth client details
