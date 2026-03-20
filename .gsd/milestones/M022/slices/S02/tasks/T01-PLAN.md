---
estimated_steps: 8
estimated_files: 4
---

# T01: Build field mapper and person matcher with tests

**Slice:** S02 — Pull sync with configurable field transforms + subtask nesting
**Milestone:** M022

## Description

Build the pure transform layer for Asana sync — `field_mapper.py` containing all field extraction and mapping logic, and `person_matcher.py` for assignee/follower email resolution. The field mapper is the core novelty of this milestone: instead of hardcoded status/priority maps (like Linear/GitHub/Todoist), it reads mapping configuration from a `field_config` dict (populated from StateClient at sync time by the sync engine). Three status extraction paths must work: `completed_only`, `custom_field`, and `section`.

Person matcher is a direct clone of `apps/linear-sync/services/person_matcher.py` — same SPARQL email lookup pattern, same create-on-miss, same LRU cache. Zero functional changes.

Both files are pure (no network, no logging side effects in the mapper). All tests are self-contained with no conftest dependency.

## Steps

1. **Read reference implementations** for patterns and structure:
   - `apps/linear-sync/services/field_mapper.py` (~358 lines) — hardcoded STATUS_MAP/PRIORITY_MAP pattern, `build_task_properties()` signature, `compute_issue_slug()`, BPKM IRI prefix
   - `apps/linear-sync/services/person_matcher.py` (~139 lines) — full clone source
   - `apps/outlook-calendar/services/field_mapper.py` — markdownify HTML→Markdown pattern (lines ~170-210)
   - `apps/asana-sync/services/asana_client.py` — understand the task dict shape returned by `get_tasks()` / `get_subtasks()` with opt_fields

2. **Create `apps/asana-sync/services/field_mapper.py`** (~350-400 lines):
   - Constants: `BPKM` IRI prefix (`urn:sempkm:model:basic-pkm:`), `COMPLETED_STATUS_MAP` (`{True: "done", False: "todo"}`), default fallback maps
   - Conditional markdownify import (same pattern as outlook-calendar: `try: from markdownify import markdownify as md` with `md = None` fallback)
   - `strip_html_tags(text)` — regex HTML strip fallback
   - `extract_body(task)` — use `html_notes` if present (convert via markdownify or strip_html_tags), fall back to `notes` (plain text passthrough). Return None if empty.
   - `extract_status(task, field_config)` — three modes based on `field_config.get("status_source")`:
     - `"completed_only"`: map `task["completed"]` boolean via COMPLETED_STATUS_MAP
     - `"custom_field"`: find the custom field in `task["custom_fields"]` where `cf["gid"] == field_config["status_field_gid"]`, get `cf["enum_value"]["name"]`, look up in `field_config["status_mapping"]` dict. If enum_value is None or not in mapping, fall back to completed boolean.
     - `"section"`: look up `section_name` parameter in `field_config["status_mapping"]` dict. Fall back to completed boolean if section_name not in mapping.
     - Default/missing status_source: fall back to completed boolean
   - `extract_priority(task, field_config)` — find custom field matching `field_config["priority_field_gid"]` in `task["custom_fields"]`, look up `enum_value.name` in `field_config["priority_mapping"]`. Return None if no match or no priority field configured.
   - `extract_story_points(task, field_config)` — find custom field matching `field_config["story_points_field_gid"]`, return `number_value` if present.
   - `extract_tags(task)` — extract `task["tags"]` list, return comma-separated `tag["name"]` string or None.
   - `extract_followers(task)` — extract from `task["followers"]` list, return list of `{"email": ..., "name": ...}` dicts.
   - `extract_assignee(task)` — extract from `task["assignee"]`, return `{"email": ..., "name": ...}` dict or None.
   - `extract_section_name(task)` — extract first section name from `task["memberships"][0]["section"]["name"]` if available.
   - `detect_milestone(task)` — return True if `task.get("resource_subtype") == "milestone"`.
   - `extract_due_date(task)` — return `due_on` (date) or truncate `due_at` (datetime) to date. Return None if neither present.
   - `extract_start_date(task)` — return `start_on` or truncate `start_at`.
   - `compute_task_slug(task)` — use `task["gid"]` to generate a stable slug like `asana-{gid}`.
   - `build_task_properties(task, field_config, section_name=None)` — main entry point. Returns a dict of bpkm property IRIs → values. Calls all extraction helpers. Includes:
     - `dcterms:title` from `task["name"]`
     - `bpkm:taskStatus` from `extract_status()`
     - `bpkm:priority` from `extract_priority()`
     - `bpkm:dueDate` from `extract_due_date()`
     - `bpkm:startDate` from `extract_start_date()`
     - `bpkm:tags` from `extract_tags()`
     - `bpkm:storyPoints` from `extract_story_points()`
     - `bpkm:externalUrl` from `task["permalink_url"]`
     - `bpkm:externalId` from `task["gid"]`
     - `bpkm:externalUuid` from `task["gid"]`
     - `bpkm:externalProvider` = `"asana"`
     - `bpkm:lastSyncedAt` = current UTC ISO timestamp
     - Only include non-None values (skip None/empty)
   - Return the detected type IRI (`bpkm:Milestone` if milestone detected, else `bpkm:Task`) alongside properties — either as a tuple `(type_iri, properties)` or include type in the return dict.

3. **Create `apps/asana-sync/services/person_matcher.py`** (~140 lines):
   - Clone from `apps/linear-sync/services/person_matcher.py`
   - Change logger name from `linear_sync.person_matcher` to `asana.sync.person_matcher`
   - Everything else stays the same: `PersonMatcher` class with `match_or_create(email, display_name)`, `_lookup_by_email()`, `_create_person()`, `_slugify()`, `_email_local_part()`

4. **Create `backend/tests/test_asana_field_mapper.py`** (~600-700 lines, 50+ tests):
   - Import the field mapper functions directly (add sys.path manipulation for the apps directory)
   - Test `extract_status()` with all 3 modes:
     - completed_only: True→done, False→todo
     - custom_field: matching GID with valid enum_value, missing GID, None enum_value, enum_value not in mapping
     - section: section_name in mapping, section_name not in mapping, empty section_name
     - Missing/default status_source falls back to completed
   - Test `extract_priority()`: matching GID, no match, None enum_value, priority not in mapping, no priority_field_gid configured
   - Test `extract_story_points()`: matching GID with number_value, no match, no story_points_field_gid
   - Test `extract_tags()`: multiple tags, single tag, empty tags list, no tags key
   - Test `extract_followers()`: multiple followers with email/name, empty, no followers key
   - Test `extract_assignee()`: present with email/name, None assignee
   - Test `extract_section_name()`: present, empty memberships, no memberships key
   - Test `detect_milestone()`: milestone subtype, default_task subtype, no subtype
   - Test `extract_body()`: html_notes with markup (verify markdown conversion), plain notes fallback, empty, None
   - Test `extract_due_date()` / `extract_start_date()`: due_on, due_at truncation, start_on, start_at truncation, neither present
   - Test `compute_task_slug()`: deterministic output from GID
   - Test `build_task_properties()`: full happy path with all fields, minimal task, milestone detection changes type, status from each mode, None values omitted
   - Use helper functions to build realistic Asana task dicts with sensible defaults

5. **Create `backend/tests/test_asana_person_matcher.py`** (~250 lines, 10+ tests):
   - Clone test structure from prior sync apps
   - Mock graph_client and command_client with async stubs
   - Test: email match found via SPARQL → returns IRI, no execute called
   - Test: no email match → creates Person, returns new IRI
   - Test: cache hit on second call → no SPARQL query
   - Test: None email → returns None
   - Test: empty email → returns None
   - Test: display_name used for slug when present
   - Test: email local part used for slug when no display_name
   - Test: multiple different emails → separate lookups
   - Test: same email different case → cache hit (case-insensitive)

6. **Run all tests:**
   ```bash
   pytest backend/tests/test_asana_field_mapper.py -v --noconftest
   pytest backend/tests/test_asana_person_matcher.py -v --noconftest
   ```

7. **Verify syntax** on all new files:
   ```bash
   python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"
   python3 -c "import ast; ast.parse(open('apps/asana-sync/services/person_matcher.py').read())"
   ```

8. **Commit:** `feat(asana-sync): field mapper with configurable transforms + person matcher`

## Must-Haves

- [ ] `field_mapper.py` handles all three status modes (completed_only, custom_field, section) reading from field_config dict
- [ ] Priority mapping reads custom field by GID and looks up enum_value.name in field_config priority_mapping
- [ ] Story points extracted from number custom field by GID
- [ ] HTML→Markdown conversion for html_notes with markdownify (conditional import, strip_html_tags fallback)
- [ ] Milestone detection via `resource_subtype: "milestone"` returns `bpkm:Milestone` type
- [ ] Tag extraction from `tags[].name` as comma-separated string
- [ ] Follower/assignee extraction returns `{email, name}` dicts
- [ ] Section name extraction from `memberships[0].section.name`
- [ ] `compute_task_slug()` produces deterministic slug from task GID
- [ ] `build_task_properties()` returns all non-None bpkm properties including externalProvider="asana", lastSyncedAt
- [ ] `person_matcher.py` cloned from Linear with SPARQL email lookup, create-on-miss, LRU cache
- [ ] 50+ field mapper tests covering all extraction paths and edge cases
- [ ] 10+ person matcher tests covering match, create, cache, None/empty email
- [ ] All tests pass with `--noconftest`
- [ ] Custom field value extraction matches by GID (not by name) — GIDs are stable, names can change
- [ ] Section membership path is `memberships[n].section.name`, not top-level
- [ ] MockResponse pattern uses `data if data is not None else {}` (KNOWLEDGE.md pattern #2)

## Verification

- `pytest backend/tests/test_asana_field_mapper.py -v --noconftest` — 50+ tests pass
- `pytest backend/tests/test_asana_person_matcher.py -v --noconftest` — 10+ tests pass
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/field_mapper.py').read())"` — no error
- `python3 -c "import ast; ast.parse(open('apps/asana-sync/services/person_matcher.py').read())"` — no error

## Inputs

- `apps/linear-sync/services/field_mapper.py` — reference architecture for BPKM prefix, property building, slug computation
- `apps/linear-sync/services/person_matcher.py` — direct clone source for person matcher
- `apps/outlook-calendar/services/field_mapper.py` (lines ~170-210) — markdownify HTML→Markdown pattern with conditional import
- `apps/asana-sync/services/asana_client.py` — understand task dict shape returned by get_tasks()/get_subtasks()
- S01 Summary forward intelligence — StateClient keys: `status_source`, `status_field_gid`, `status_mapping`, `priority_field_gid`, `priority_mapping`, `story_points_field_gid`. Three status modes: completed_only, custom_field, section.
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §1 — Asana field/entity/status/priority mapping tables

## Observability Impact

- **No runtime signals** — both `field_mapper.py` and `person_matcher.py` are pure / injected-dependency modules with no direct logging or state persistence. The person matcher uses `logger.debug()` for cache hits and person creation, but these are diagnostic only and produce no new runtime surfaces.
- **Future agent inspection:** To verify field mapper correctness, run the test suite. To inspect person matcher behavior at runtime, check `asana.sync.person_matcher` log output at DEBUG level.
- **Failure state:** Field mapper functions return None / fallback values on missing data — no exceptions. Person matcher returns None for empty/None email. Both are designed for the sync engine (T02) to handle errors at the orchestration layer.

## Expected Output

- `apps/asana-sync/services/field_mapper.py` — ~350-400 lines, pure functions for all Asana→bpkm:Task field transforms with configurable status/priority
- `apps/asana-sync/services/person_matcher.py` — ~140 lines, SPARQL email lookup + create-on-miss + LRU cache
- `backend/tests/test_asana_field_mapper.py` — ~600-700 lines, 50+ tests covering all extraction paths
- `backend/tests/test_asana_person_matcher.py` — ~250 lines, 10+ tests covering match/create/cache patterns
