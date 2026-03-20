---
estimated_steps: 8
estimated_files: 3
---

# T01: Build ADF↔Markdown converter with 60+ unit tests

**Slice:** S01 — ADF converter + field mapper + Jira client + auth scaffold
**Milestone:** M023

## Description

Build the Atlassian Document Format (ADF) ↔ Markdown converter as a pure Python module. ADF is Jira Cloud v3's JSON-based rich text format — all issue descriptions arrive as ADF and must be sent back as ADF. This is the highest-risk component in M023 and must be proven with comprehensive tests before other modules build on it.

The converter is a pure module with zero dependencies on the App SDK, network, or state — making it ideal to build and test first.

**Key design decisions:**
- D234: Hand-roll a ~300-line recursive converter covering ~12 common ADF node types
- Unknown node types emit `[unsupported: {type}]` placeholder — never crash
- Markdown→ADF reverse direction only handles the subset SemPKM produces (paragraphs, headings, lists, code blocks, links)

## Steps

1. Create `apps/jira-sync/services/__init__.py` (empty file) and `apps/jira-sync/services/adf_converter.py`
2. Implement `adf_to_markdown(adf_doc: dict | None) -> str` as a recursive converter:
   - Top-level: iterate `doc["content"]` array, converting each block node
   - **Block nodes:** `paragraph`, `heading` (levels 1-6 → `#`), `bulletList` (→ `- items`), `orderedList` (→ `1. items`), `codeBlock` (→ triple backtick with optional language attr), `blockquote` (→ `> lines`), `table` (→ pipe-delimited Markdown table with header separator), `rule` (→ `---`), `mediaGroup` (→ `[media: {id}]` placeholder)
   - **Inline nodes:** `text` with marks (strong→`**`, em→`*`, code→backtick, strike→`~~`, link→`[text](url)`, textColor→pass through text), `mention` (→ `@{text}`), `inlineCard` (→ `[{url}]({url})` or `[link]({url})`)
   - **Nesting:** `listItem` contains block content (recursion). Nested lists must track indent level. `tableRow` → row, `tableCell`/`tableHeader` → cells
   - **Unknown types:** emit `[unsupported: {type}]` and continue processing — never raise
   - **Edge cases:** None/empty input → empty string. Missing `content` key → empty string. Empty text nodes → skip
3. Implement `markdown_to_adf(md_text: str) -> dict` for the reverse direction:
   - Parse Markdown line-by-line (simple state machine, no dependency on markdown libraries)
   - Handle: paragraphs (text between blank lines), headings (`#`→heading with level attr), bullet lists (`- `→bulletList), ordered lists (`1. `→orderedList), code blocks (triple backtick→codeBlock with language), links (`[text](url)`→text with link mark)
   - Return valid ADF document structure: `{"version": 1, "type": "doc", "content": [...]}`
   - Unknown/complex Markdown → wrap in paragraph node
4. Create `backend/tests/test_jira_adf_converter.py` using importlib loading pattern (matching `test_github_field_mapper.py`):
   - Load module from `apps/jira-sync/services/adf_converter.py` via `importlib.util.spec_from_file_location`
   - Build helper `_make_adf_doc(*content_nodes)` that wraps nodes in `{"version": 1, "type": "doc", "content": [...]}`
5. Write tests for `adf_to_markdown` — at least 2 per node type:
   - paragraph: simple text, text with inline marks
   - heading: levels 1-6, heading with marks
   - bulletList: flat, nested, with inline formatting
   - orderedList: simple, multi-item
   - codeBlock: with language, without language, with content
   - blockquote: simple, multi-line
   - table: header + data rows, cells with inline content
   - text marks: strong, em, code, strike, link, combined marks
   - mention: with text attribute, with id fallback
   - inlineCard: with url
   - mediaGroup: placeholder output
   - rule: horizontal rule
   - unknown type: emits placeholder
   - null/empty: None input, empty doc, empty content array
6. Write tests for `markdown_to_adf`:
   - Paragraphs, headings (levels 1-3), bullet lists, ordered lists, code blocks with language, links
   - Empty/None input → valid empty ADF doc
   - Mixed content document
7. Write round-trip tests: `adf_to_markdown(adf_doc)` → `markdown_to_adf(md)` → verify structure is close (not exact — lossy conversion is expected)
8. Run all tests and fix any failures

## Must-Haves

- [ ] `adf_to_markdown()` handles all 12 common ADF node types without crashing
- [ ] Unknown ADF node types produce `[unsupported: {type}]` placeholder
- [ ] `markdown_to_adf()` handles paragraphs, headings, lists, code blocks, links
- [ ] Null/empty input handled gracefully (returns empty string or empty doc)
- [ ] 60+ unit tests pass
- [ ] Module loadable via importlib from test directory

## Verification

- `cd backend && python -m pytest tests/test_jira_adf_converter.py -v` — all 60+ tests pass
- `python -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('x', 'apps/jira-sync/services/adf_converter.py'); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); print('OK')"` — module loads cleanly

## Inputs

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` §4 "Description Format" — ADF node type documentation
- `apps/github-sync/services/field_mapper.py` — reference for pure-module pattern
- `backend/tests/test_github_field_mapper.py` — reference for importlib test loading pattern
- D234 decision — hand-roll converter covering ~12 common ADF node types

## Observability Impact

- **Signals changed:** None — this is a pure module with no runtime logging or state. All functions are side-effect-free.
- **Inspection surface:** `adf_to_markdown()` and `markdown_to_adf()` are deterministic pure functions — output can be inspected by calling them with sample data. Unknown ADF nodes produce `[unsupported: {type}]` markers in output, visible in any rendered description.
- **Failure visibility:** Unknown node types never raise — they emit placeholder text. Invalid input (None, missing keys) returns empty string/doc. Test suite covers all edge cases.
- **Future agent verification:** Run `cd backend && python -m pytest tests/test_jira_adf_converter.py -v` to verify all 60+ tests pass. Module loads cleanly via importlib.

## Expected Output

- `apps/jira-sync/services/__init__.py` — empty package init
- `apps/jira-sync/services/adf_converter.py` — ~300-400 line pure module with `adf_to_markdown()` and `markdown_to_adf()`
- `backend/tests/test_jira_adf_converter.py` — 60+ unit tests covering all node types and edge cases
