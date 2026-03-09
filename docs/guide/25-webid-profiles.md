# Chapter 25: WebID Profiles

A WebID is a URI that identifies you on the web and resolves to a machine-readable profile document. SemPKM generates a WebID for each user, publishing your identity in a format that supports decentralized authentication, fediverse verification, and linked data interoperability.

This chapter explains how WebID profiles work, how to set yours up, and how to use it for fediverse verification.

---

## What Is a WebID?

A WebID is a URL that serves dual purposes:

1. **Human-readable profile** -- when you visit the URL in a browser, you see an HTML page with your name, public key, and links
2. **Machine-readable identity** -- when an RDF client requests the same URL, it receives a structured document describing you using FOAF and security vocabularies

This makes your identity portable. Any service that understands WebID can verify who you are by fetching your profile URL and reading the RDF data.

---

## Your WebID URI

Each user's WebID follows the pattern:

```
https://your-instance/users/username#me
```

The `#me` fragment identifier is significant. It distinguishes the **person** (the `#me` fragment) from the **profile document** (the URL without the fragment). When a client fetches `https://your-instance/users/alice`, it receives the profile document. The `#me` fragment tells the client "the person described here is identified by this URI."

The profile document URL (without `#me`) is:

```
https://your-instance/users/username
```

---

## Setting Up Your WebID

To create your WebID profile:

1. Navigate to **Settings > Identity**
2. Enter a **username** -- this becomes part of your WebID URI and cannot be changed after creation
3. Click **Claim Username**

When you claim a username, SemPKM automatically generates an **Ed25519 key pair** for you. The public key is included in your profile document. The private key is encrypted and stored securely.

> **Important:** Your username is immutable once set. Choose carefully -- it becomes a permanent part of your identity URI.

---

## Publishing Your Profile

After claiming a username, your profile exists but is not publicly accessible by default. To make it visible:

1. Go to **Settings > Identity**
2. Click **Publish Profile**

Once published, anyone can visit your profile URL to see your public information. Unpublishing hides your profile (returns 404 to visitors) but does not delete it.

---

## Content Negotiation

Your profile URL serves different formats depending on how it is requested. This is called **content negotiation** and is a core feature of linked data.

### Browser request (HTML)

When you visit your profile URL in a browser, you see an HTML page showing:

- Your display name
- Your WebID URI
- Your public key fingerprint
- Your `rel="me"` links (for fediverse verification)
- Links to the IndieAuth metadata endpoint

### RDF client request (Turtle)

When an RDF client sends `Accept: text/turtle`, your profile is returned as a Turtle document:

```turtle
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix sec: <https://w3id.org/security#> .

<https://your-instance/users/alice>
    a foaf:PersonalProfileDocument ;
    foaf:primaryTopic <https://your-instance/users/alice#me> .

<https://your-instance/users/alice#me>
    a foaf:Person ;
    foaf:name "Alice" ;
    sec:hasKey <https://your-instance/users/alice#me-key> .

<https://your-instance/users/alice#me-key>
    a sec:Ed25519VerificationKey2020 ;
    sec:controller <https://your-instance/users/alice#me> ;
    sec:publicKeyPem "-----BEGIN PUBLIC KEY-----\n..." .
```

### JSON-LD request

When a client sends `Accept: application/ld+json`, the same data is returned as JSON-LD.

### Query parameter fallback

If you cannot control the `Accept` header, use a query parameter:

- `?format=turtle` -- returns Turtle
- `?format=jsonld` -- returns JSON-LD

---

## Fediverse Verification (rel="me")

You can use your WebID profile for bidirectional verification on Mastodon and other fediverse platforms that support `rel="me"` links.

### How it works

1. **Add your fediverse profile URL to SemPKM**: Go to **Settings > Identity** and add your Mastodon profile URL (e.g., `https://mastodon.social/@alice`) as a `rel="me"` link.

2. **Add your WebID URL to your fediverse profile**: In your Mastodon profile settings, add your SemPKM profile URL (e.g., `https://your-instance/users/alice`) as a profile link.

3. **Verification completes automatically**: Mastodon fetches your SemPKM profile page, finds the `rel="me"` link pointing back to your Mastodon profile, and marks the link as verified (green checkmark).

This creates a bidirectional proof of ownership -- your SemPKM profile links to your Mastodon account, and your Mastodon account links back to your SemPKM profile.

### Managing links

In **Settings > Identity**, you can add, remove, and reorder your `rel="me"` links. Each link appears on your public profile page and is included in the RDF profile as `foaf:account` values.

---

## Cryptographic Keys

Each WebID profile includes an Ed25519 public key. This key serves as a cryptographic identity anchor for future features such as signed requests and federation.

### Key details

- **Algorithm:** Ed25519 (Edwards-curve Digital Signature Algorithm)
- **Format:** PEM-encoded SubjectPublicKeyInfo
- **RDF type:** `sec:Ed25519VerificationKey2020`
- **Storage:** The public key is published in the profile. The private key is encrypted with Fernet (PBKDF2-derived from the application secret key) and stored in the database.

### Key fingerprint

Your key's SHA-256 fingerprint is displayed in **Settings > Identity** as a colon-separated hex string (e.g., `ab:cd:ef:12:34:...`). This makes it easy to verify your key out-of-band.

### Regenerating keys

If you need a new key pair (e.g., if the private key may have been compromised), go to **Settings > Identity** and click **Regenerate Key**. This replaces both the public and private keys. Any service that cached your old public key will need to re-fetch your profile.

---

## For Advanced Users

### Verifying a profile with curl

Fetch the Turtle representation:

```bash
curl -H "Accept: text/turtle" https://your-instance/users/alice
```

Fetch JSON-LD:

```bash
curl -H "Accept: application/ld+json" https://your-instance/users/alice
```

Or use the query parameter:

```bash
curl "https://your-instance/users/alice?format=turtle"
```

### RDF vocabulary

The profile document uses:

- **FOAF** (`http://xmlns.com/foaf/0.1/`) -- `Person`, `PersonalProfileDocument`, `name`, `account`, `primaryTopic`
- **W3C Security Vocabulary** (`https://w3id.org/security#`) -- `Ed25519VerificationKey2020`, `publicKeyPem`, `controller`, `hasKey`

### IndieAuth discovery

Your profile page includes HTTP `Link` headers and HTML `<link>` elements for IndieAuth endpoint discovery:

- `rel="indieauth-metadata"` -- points to the metadata endpoint
- `rel="authorization_endpoint"` -- the authorization endpoint
- `rel="token_endpoint"` -- the token endpoint

These headers enable IndieAuth clients to discover how to authenticate against your SemPKM instance. See [Chapter 26: IndieAuth](26-indieauth.md) for details.

---

## See Also

- [Chapter 26: IndieAuth](26-indieauth.md) -- use your WebID to sign into IndieWeb-compatible services
- [Chapter 13: Settings](13-settings.md) -- manage your identity settings
- [Appendix A: Environment Variable Reference](appendix-a-environment-variables.md) -- configure `APP_BASE_URL` for correct WebID URIs

---

**Previous:** [Chapter 24: Obsidian Import](24-obsidian-onboarding.md) | **Next:** [Chapter 26: IndieAuth](26-indieauth.md)
