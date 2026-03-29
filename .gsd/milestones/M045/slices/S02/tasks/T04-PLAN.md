---
estimated_steps: 12
estimated_files: 1
skills_used: []
---

# T04: Caddyfile CSP cleanup and HSTS header

Remove stale CDN domains from Caddyfile.cloud CSP directives and add HSTS header for cloud deployments.

## Steps

1. Edit `Caddyfile.cloud` header block:
   - In Content-Security-Policy, remove `https://unpkg.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com` from `script-src` directive
   - Result: `script-src 'self' 'unsafe-inline'`
   - Same removal from `style-src` directive
   - Result: `style-src 'self' 'unsafe-inline'`
   - Add `Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"` to the header block

## Must-Haves

- [ ] CSP `script-src` contains no CDN domains
- [ ] CSP `style-src` contains no CDN domains
- [ ] HSTS header present with max-age >= 63072000

## Inputs

- ``Caddyfile.cloud` — current CSP with stale CDN domains on line 20, no HSTS`

## Expected Output

- ``Caddyfile.cloud` — clean CSP without CDN domains, HSTS header added`

## Verification

! grep -q 'unpkg.com\|cdn.jsdelivr.net\|cdnjs.cloudflare.com' Caddyfile.cloud && grep -q 'Strict-Transport-Security' Caddyfile.cloud
