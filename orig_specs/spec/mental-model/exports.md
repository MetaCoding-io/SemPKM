# Exports and Cross-Model Embedding (v1)

- Cross-model embedding is **private-by-default**.
- A model may embed another model’s view/dashboard only if that view/dashboard is explicitly exported.

## Manifest
Exports are declared in `manifest.yaml`:

```yaml
exports:
  views:
    - "view:reading_queue"
  dashboards:
    - "dashboard:project"