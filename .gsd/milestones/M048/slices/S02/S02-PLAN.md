# S02: Diff-Based Save — No Phantom Events

**Goal:** Eliminate phantom save events by diffing current property values against the triplestore before patching, and by skipping body saves when content is unchanged.
**Demo:** After this: Open an object, change one property field, save. Check the event log — only the changed property appears. Change nothing and save — no event is created.

## Tasks
