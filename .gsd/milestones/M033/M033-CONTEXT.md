# M033: Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul

## Summary

Seven feature areas spanning SPARQL federation, new view renderers, app catalog, and deployment infrastructure.

## Scope

1. **Federated SPARQL with mirrored triples** — SERVICE clause pass-through, cache-and-mirror layer in `urn:sempkm:mirrored`, configurable endpoint allowlist, provenance tracking, SPARQL console SERVICE assistance
2. **Isometric 2.5D graph view** — New Cytoscape.js layout with CSS 3D transforms, configurable z-layer dimension, translucent layer planes, cross-layer edges
3. **Calendar view** — FullCalendar 6.x lazy-loaded, new generic view renderer, SPARQL temporal query builder, month/week/day views, type filter pills
4. **Map view** — Leaflet.js + OpenStreetMap, marker clustering, popup with object info, graceful tile degradation
5. **Rich app catalog pages** — Detail pages per app with description, screenshots, features, permissions, install/uninstall
6. **Graph view icon toggle** — Toolbar button for shape-only vs Lucide SVG icon-on-node display
7. **Deployment & onboarding** — Setup wizard, `docker-compose.cloud.yml` with Caddy for HTTPS, mkcert for local TLS, BASE_NAMESPACE auto-configuration

## Dependencies

- M032 (Block-Based Custom UI Builder)

## Design References

- `.gsd/design/DEPLOYMENT-AND-ONBOARDING-DESIGN.md`
