---
created: 2026-02-23T22:24:41.362Z
title: Add edit form helptext property to SHACL types
area: ui
files:
  - backend/app/services/shapes.py
  - backend/app/templates/forms/object_form.html
  - orig_specs/models/starter-basic-pkm/shapes.ttl
---

## Problem

When users open the edit form for an object, there's no contextual guidance about what the fields mean, what relationships are for, or how to use the form effectively. Each object type (Note, Project, Concept, Person) has different fields and relationships that may not be self-explanatory.

## Solution

Add a custom SHACL annotation property (e.g., `sempkm:editHelpText`) to each NodeShape that contains markdown-formatted help text. The implementation would:

1. Define `sempkm:editHelpText` as a string property on NodeShapes in shapes.ttl
2. Extend `ShapesService.get_form_for_type()` to load this property into `NodeShapeForm`
3. Pass the helptext through to `object_form.html`
4. Render it as a collapsible markdown section (collapsed by default) at the top of the edit form, using the same marked.js rendering pipeline as the read view

Model authors would write helptext like:
```turtle
ex:NoteShape a sh:NodeShape ;
  sempkm:editHelpText """## Creating a Note
- **Title**: A descriptive title for your note
- **Type**: idea, reference, meeting, or journal
- **About Concepts**: Tag with relevant concepts for discoverability
""" .
```
