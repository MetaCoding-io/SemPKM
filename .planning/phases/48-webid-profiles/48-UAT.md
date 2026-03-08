---
status: complete
phase: 48-webid-profiles
source: 48-01-SUMMARY.md, 48-02-SUMMARY.md
started: 2026-03-08T06:00:00Z
updated: 2026-03-08T06:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Start from scratch. Server boots without errors, migration 005 completes, settings page loads.
result: pass

### 2. Claim Username
expected: In Settings, find WebID Profile section. Enter a username and submit. Username is saved and displayed. Attempting to change it after claiming shows an error (username is immutable).
result: pass

### 3. Key Generation & Display
expected: After claiming username, Ed25519 key pair is auto-generated. Settings shows public key fingerprint (colon-separated hex). A way to copy the public key PEM is available.
result: pass

### 4. Manage Profile Links
expected: In WebID settings, you can add rel="me" links (e.g. GitHub, Mastodon URLs). Added links appear in the list. Links can be removed.
result: pass

### 5. Publish Toggle
expected: A publish/unpublish toggle controls whether your profile is publicly visible. When unpublished, the checkbox should be unchecked and labeled to indicate the profile is not published. When published, checkbox is checked. The label should remain stable (not change text when toggled).
result: issue
reported: "The labeling is confusing, the text should not change. It should just say Published and if its unchecked the user will get that its not published"
severity: minor

### 6. Public Profile HTML Page
expected: With profile published, visiting /users/{username} in browser shows a standalone HTML profile page with SemPKM branding, your username, public key fingerprint, and any rel="me" links.
result: pass

### 7. Content Negotiation (Turtle)
expected: Requesting /users/{username} with Accept: text/turtle header returns valid Turtle RDF containing FOAF and W3C Security vocabulary triples.
result: pass

### 8. Content Negotiation (JSON-LD)
expected: Requesting /users/{username} with Accept: application/ld+json header returns valid JSON-LD with profile data.
result: pass

### 9. Unpublished Profile Returns 404
expected: With profile unpublished, visiting /users/{username} returns 404 (not the profile page).
result: pass

## Summary

total: 9
passed: 8
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Publish toggle label should remain stable and just say 'Published' with checkbox state indicating status"
  status: failed
  reason: "User reported: The labeling is confusing, the text should not change. It should just say Published and if its unchecked the user will get that its not published"
  severity: minor
  test: 5
  artifacts: []
  missing: []
