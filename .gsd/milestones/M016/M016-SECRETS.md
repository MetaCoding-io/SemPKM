# Secrets Manifest

**Milestone:** 
**Generated:** 

### LINEAR_CLIENT_ID

**Service:** 
**Status:** skipped
**Destination:** dotenv

1. Sign in to Linear at https://linear.app
2. Navigate to Settings → API (or go directly to https://linear.app/settings/api/applications)
3. Click "+ New OAuth application"
4. Set Application name: "SemPKM Linear Sync"
5. Set Callback URL: `http://localhost:3000/app/linear-sync/_fragments/oauth-callback`
6. Click "Create"
7. Copy the Client ID

### LINEAR_CLIENT_SECRET

**Service:** 
**Status:** skipped
**Destination:** dotenv

1. From the same OAuth application created above
2. Copy the Client Secret (shown once at creation time)

### LINEAR_API_KEY (alternative to OAuth)

**Service:** 
**Status:** collected
**Destination:** dotenv

1. Sign in to Linear at https://linear.app
2. Navigate to Settings → Account → Security & Access (or https://linear.app/settings/account/security)
3. Under "Personal API keys", click "Create key"
4. Enter a label: "SemPKM Sync"
5. Copy the generated API key
