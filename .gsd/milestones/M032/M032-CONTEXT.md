# M032: Block-Based Custom UI Builder

## Summary

Research and design for a Notion/Zabbix-inspired block composition system. Users build custom dashboards, views, and multi-object creation forms by arranging reusable widget blocks.

## Scope

- RDF data model for block layouts
- Widget type registry and config schemas
- Layout engine approach (GridStack.js for drag-drop-resize grid)
- Custom SHACL-form blocks for multi-object creation workflows
- Auto-migration of existing fixed CSS Grid dashboards to GridStack positions

## Deliverables

- Research document (Notion/Zabbix survey)
- Design document (RDF data model, widget registry, form semantics)
- GridStack layout engine replacing fixed CSS Grid
- Block registry with typed widget declarations
- Data-driven widgets: stat-card, chart, heading
- Multi-object form groups with slot-based IRI resolution
- Widget inventory with config schemas

## Dependencies

- M031 (Views Overhaul) — complete
