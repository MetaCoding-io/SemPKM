# Chapter 26: IndieAuth

IndieAuth is an OAuth 2.0-based authentication protocol that uses your URL as your identity. SemPKM acts as an IndieAuth provider, letting you sign into IndieWeb-compatible services using your WebID profile URL -- no separate account required.

This chapter explains how IndieAuth works, what happens when an app requests authorization, and how to manage authorized applications.

---

## How It Works

IndieAuth follows a standard OAuth 2.0 authorization code flow with PKCE (Proof Key for Code Exchange). Here is what happens when you sign into an IndieWeb app using your SemPKM identity:

1. **You enter your profile URL** into the app's login form (e.g., `https://your-instance/users/alice`)
2. **The app discovers your endpoints** by fetching your profile page and reading the `rel="indieauth-metadata"` link
3. **The app redirects you to SemPKM** with an authorization request containing the app's identity, requested permissions, and a PKCE challenge
4. **SemPKM shows a consent screen** displaying the app name, its URL, and what permissions it is requesting
5. **You approve or deny** the request
6. **SemPKM redirects back to the app** with an authorization code
7. **The app exchanges the code for a token** by calling SemPKM's token endpoint with the PKCE verifier
8. **The app can now act on your behalf** within the approved scope

The entire flow happens in your browser. You never share your SemPKM password with the requesting app.

---

## Discovery

IndieAuth clients discover your authorization and token endpoints automatically. Your WebID profile page (see [Chapter 25: WebID Profiles](25-webid-profiles.md)) includes:

- An HTTP `Link` header with `rel="indieauth-metadata"` pointing to the metadata endpoint
- The metadata endpoint returns a JSON document listing all endpoints and capabilities

### Metadata endpoint

The metadata endpoint is at `/api/indieauth/metadata` and returns:

```json
{
  "issuer": "https://your-instance",
  "authorization_endpoint": "https://your-instance/api/indieauth/authorize",
  "token_endpoint": "https://your-instance/api/indieauth/token",
  "introspection_endpoint": "https://your-instance/api/indieauth/introspect",
  "code_challenge_methods_supported": ["S256"],
  "scopes_supported": ["profile", "email"],
  "response_types_supported": ["code"],
  "grant_types_supported": ["authorization_code", "refresh_token"],
  "authorization_response_iss_parameter_supported": true
}
```

The `.well-known/oauth-authorization-server` path redirects to this metadata endpoint per RFC 8414.

---

## The Consent Screen

When an app requests authorization, SemPKM shows a consent screen. This screen displays:

- **App name and URL** -- fetched from the app's `client_id` URL. If the app publishes an `h-app` microformat, its name and logo are shown. Otherwise, the page title or hostname is used.
- **Requested scopes** -- each permission the app is asking for, with a description of what it grants
- **Your identity** -- your profile URL, confirming which account the app will access
- **Approve / Deny buttons** -- you choose whether to grant the app access

If you are not currently logged in, SemPKM redirects you to the login page first, then back to the consent screen after authentication.

---

## Supported Scopes

SemPKM's IndieAuth provider currently supports these scopes:

| Scope | Description | Claims |
|-------|-------------|--------|
| `profile` | Access your profile information | name, photo, URL |
| `email` | Access your email address | email |

Apps request one or more scopes during authorization. Unknown scopes are silently dropped per the IndieAuth specification. You can see exactly which permissions each app has been granted.

---

## Managing Authorized Apps

After you approve an app, it receives tokens that let it access your profile. You can view and revoke these authorizations.

### Viewing authorized apps

Go to **Settings > Identity**. The authorized applications section lists all apps with active tokens, showing:

- App name (or `client_id` URL if the name could not be fetched)
- Granted scopes
- When the authorization was created
- When the token expires

### Revoking access

To revoke an app's access, click the **Revoke** button next to its entry. This immediately invalidates the app's tokens. The app will need to request authorization again to regain access.

---

## Token Lifecycle

IndieAuth tokens have specific lifetimes:

| Token Type | Lifetime | Purpose |
|------------|----------|---------|
| Authorization code | 60 seconds | Single-use, exchanged for tokens |
| Access token | 1 hour | Grants API access |
| Refresh token | 30 days | Used to obtain new access tokens |

When an access token expires, the app can use its refresh token to obtain a new access token without requiring you to re-authorize. Refresh tokens are rotated on each use -- the old refresh token is invalidated and a new one is issued.

---

## Security Features

SemPKM's IndieAuth implementation includes several security measures:

- **PKCE required (S256):** Every authorization request must include a PKCE code challenge using the SHA-256 method. This prevents authorization code interception attacks.
- **Single-use authorization codes:** Each code can only be exchanged once and expires after 60 seconds.
- **Refresh token rotation:** Each refresh token use issues a new refresh token and invalidates the old one, limiting the window for token theft.
- **SSRF protection:** When fetching client application metadata, SemPKM rejects requests to loopback addresses to prevent server-side request forgery.
- **Hash-only storage:** Authorization codes and tokens are stored as SHA-256 hashes. The plaintext values are only returned once during issuance.

---

## For Advanced Users

### Endpoint URLs

| Endpoint | URL | Auth Required |
|----------|-----|---------------|
| Metadata | `/api/indieauth/metadata` | No |
| Authorization | `/api/indieauth/authorize` | Yes (session) |
| Token | `/api/indieauth/token` | No |
| Introspection | `/api/indieauth/introspect` | No |
| Token list | `/api/indieauth/tokens` | Yes (session) |
| Token revoke | `/api/indieauth/tokens/{id}` | Yes (session) |

### Testing with IndieAuth tools

You can test your IndieAuth setup using tools like [IndieLogin.com](https://indielogin.com) or any IndieWeb-compatible app that supports IndieAuth.

To test manually:

1. Make sure `APP_BASE_URL` is set to your instance's public URL (see [Appendix A](appendix-a-environment-variables.md))
2. Ensure your WebID profile is published (see [Chapter 25](25-webid-profiles.md))
3. Enter your profile URL into the IndieAuth client

### Token exchange example

For app developers integrating with SemPKM, here is the token exchange flow:

```bash
# Exchange authorization code for tokens
curl -X POST https://your-instance/api/indieauth/token \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE" \
  -d "client_id=https://your-app.example/" \
  -d "redirect_uri=https://your-app.example/callback" \
  -d "code_verifier=YOUR_PKCE_VERIFIER"
```

The response includes:

```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "scope": "profile",
  "me": "https://your-instance/users/alice",
  "expires_in": 3600,
  "refresh_token": "..."
}
```

### Introspection

Resource servers can verify tokens using the introspection endpoint:

```bash
curl -X POST https://your-instance/api/indieauth/introspect \
  -d "token=ACCESS_TOKEN"
```

Returns `{"active": true, ...}` for valid tokens or `{"active": false}` for expired/invalid tokens.

---

## Troubleshooting

### "Profile not found" when entering your URL

Make sure your WebID profile is published. Go to **Settings > Identity** and click **Publish Profile**. Also verify that `APP_BASE_URL` is set correctly -- if it does not match the URL you entered, the profile lookup will fail.

### Consent screen shows URL instead of app name

The app's `client_id` URL does not publish an `h-app` microformat or a `<title>` tag. This is a cosmetic issue -- the authorization flow still works correctly.

### "PKCE verification failed"

The app sent a `code_verifier` that does not match the original `code_challenge`. This is usually a bug in the client app, not in SemPKM. Ensure the app is using S256 PKCE correctly per RFC 7636.

### CORS errors

If a client-side JavaScript app is trying to call the token endpoint directly, it may encounter CORS errors. The token endpoint is designed for server-to-server communication. Client-side apps should use a backend proxy for the token exchange.

### Cookie issues in iframes

Some browsers block third-party cookies, which can prevent the consent screen from recognizing your session when loaded in an iframe. If this happens, open the authorization URL in a new tab or window instead.

---

## See Also

- [Chapter 25: WebID Profiles](25-webid-profiles.md) -- set up the profile that IndieAuth uses for identity
- [Chapter 13: Settings](13-settings.md) -- manage identity settings and authorized apps
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) -- configure `APP_BASE_URL`

---

**Previous:** [Chapter 25: WebID Profiles](25-webid-profiles.md) | **Next:** [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md)
