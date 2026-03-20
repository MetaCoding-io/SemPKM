---
id: T01
parent: S01
milestone: M023
provides:
  - adf_to_markdown() handling 12+ ADF node types
  - markdown_to_adf() handling paragraphs, headings, lists, code blocks, links, blockquotes, rules
  - 95 unit tests covering all node types, edge cases, and round-trips
key_files:
  - apps/jira-sync/services/adf_converter.py
  - apps/jira-sync/services/__init__.py
  - backend/tests/test_jira_adf_converter.py
key_decisions:
  - Hand-rolled recursive converter (~400 lines) covering 12 block types + 5 inline types with marks
  - Markdown→ADF uses line-by-line state machine with regex for inline formatting (no external markdown library)
  - Link mark applied last in mark processing to properly wrap formatted text
patterns_established:
  - ADF block node dispatch via type string to dedicated converter functions
  - importlib-based test loading for apps/ modules (matches github-sync pattern)
  - _make_adf_doc() / _text() / _para() / _heading() / _list_item() test helpers for concise ADF construction
observability_surfaces:
  - none (pure module — no runtime logging, no state, no network)
duration: 25m
verification_result: passed
completed_at: 2026-03-19
blocker_discovered: false
---

# T01: Build ADF↔Markdown converter with 60+ unit tests

**Implemented ADF↔Markdown bidirectional converter with 95 passing unit tests covering all 12 ADF node types, inline marks, edge cases, and round-trips**

## What Happened

Built `apps/jira-sync/services/adf_converter.py` as a pure Python module with two public functions:

1. **`adf_to_markdown(adf_doc)`** — recursive converter handling 12 block node types (paragraph, heading, bulletList, orderedList, codeBlock, blockquote, table, rule, mediaGroup, mediaSingle) and 5 inline node types (text with 7 mark types, mention, inlineCard, hardBreak, emoji). Unknown types emit `[unsupported: {type}]` placeholder. Nested lists track indent level. Tables produce pipe-delimited Markdown with header separator.

2. **`markdown_to_adf(md_text)`** — line-by-line state machine parsing paragraphs, headings (1-6), bullet lists (`-`, `*`, `+`), ordered lists, code blocks with language, blockquotes, horizontal rules, and inline formatting (bold, italic, code, strikethrough, links). Returns valid ADF document structure.

Created 95 tests organized into 22 test classes covering: null/empty input (6), paragraphs (5), headings (7), bullet lists (4), ordered lists (2), code blocks (4), blockquotes (2), tables (3), text marks (9), mentions (3), inline cards (3), media groups (3), rules (2), unknown types (3), misc inline (2), complex documents (2), MD→ADF empty (4), MD→ADF paragraphs (2), MD→ADF headings (3), MD→ADF lists (8), MD→ADF code blocks (3), MD→ADF links (2), MD→ADF blockquotes (2), MD→ADF rules (2), MD→ADF mixed (2), MD→ADF inline formatting (4), round-trips (6).

## Verification

All must-haves verified:
- ✅ `adf_to_markdown()` handles all 12+ common ADF node types without crashing
- ✅ Unknown ADF node types produce `[unsupported: {type}]` placeholder
- ✅ `markdown_to_adf()` handles paragraphs, headings, lists, code blocks, links
- ✅ Null/empty input handled gracefully
- ✅ 95 unit tests pass (exceeds 60+ target)
- ✅ Module loadable via importlib from test directory

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && uv run python -m pytest tests/test_jira_adf_converter.py -v` | 0 | ✅ pass (95 passed) | 0.15s |
| 2 | `python3 -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('x', 'apps/jira-sync/services/adf_converter.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('OK')"` | 0 | ✅ pass | <1s |

Slice-level checks (T01 scope only — other test files not yet created):

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && python -m pytest tests/test_jira_adf_converter.py -v` | 0 | ✅ pass (95/95) | 0.15s |
| 2 | `tests/test_jira_field_mapper.py` | — | ⬜ not yet created (T02) | — |
| 3 | `tests/test_jira_client.py` | — | ⬜ not yet created (T03) | — |
| 4 | `tests/test_jira_auth.py` | — | ⬜ not yet created (T03) | — |
| 5 | `tests/test_jira_person_matcher.py` | — | ⬜ not yet created (T03) | — |

## Diagnostics

Pure module with no runtime state. To inspect converter behavior:
- Call `adf_to_markdown(adf_dict)` with sample ADF JSON to see Markdown output
- Call `markdown_to_adf(md_string)` to see generated ADF structure
- Unknown node types appear as `[unsupported: {type}]` in Markdown output — grep for this pattern to find unsupported content

## Deviations

None. Implementation followed the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `apps/jira-sync/services/__init__.py` — empty package init
- `apps/jira-sync/services/adf_converter.py` — ~400 line pure module with `adf_to_markdown()` and `markdown_to_adf()`
- `backend/tests/test_jira_adf_converter.py` — 95 unit tests covering all node types, edge cases, and round-trips
- `.gsd/milestones/M023/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
