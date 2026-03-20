---
estimated_steps: 8
estimated_files: 3
---

# T02: Sidebar AI Insights rendering with progressive loading

**Slice:** S02 — Extension sidebar AI Insights UI
**Milestone:** M028

## Description

Build the AI Insights UI section in the sidebar — the primary user-visible feature of this slice. When the sidebar opens, it shows context results (existing behavior), then initiates the AI pipeline and progressively renders each section as results arrive from the service worker via `aiInsightsProgress` messages.

The sidebar uses vanilla JS with no frameworks — it follows the existing pattern of DOM element creation via `document.createElement()` and the `_renderGroup()` / `_renderCard()` helper pattern already in `sidebar.js`. The new AI section goes below the existing `#results` div.

**Design constraints:**
- Side panel width is 250–400px — all content must work within this narrow width
- Collapsible sections are essential to manage vertical space
- Progressive loading means each section appears independently as its API call completes
- Generation ID from T01 must be checked before rendering to prevent stale updates

**Key UX pattern:** The loading state shows contextual text that changes as each step progresses: "Analyzing page..." → "Matching against your graph..." → "Finding relationships..." → "Generating summary..." → hidden when complete.

## Steps

1. **Update sidebar.html.** Add the AI Insights container after `#evidence-prompt` and before `</main>`:
   ```html
   <div id="ai-insights" hidden>
     <div class="ai-section-header">
       <button id="ai-toggle" class="group-header" aria-expanded="true">
         <span class="group-chevron">▾</span>
         <span class="group-title">AI Insights</span>
         <span id="ai-status-badge" class="group-count" hidden></span>
       </button>
     </div>
     <div id="ai-body">
       <div id="ai-unavailable" class="ai-message" hidden>
         <div class="ai-message-icon">🔒</div>
         <p class="ai-message-text">AI features require LLM configuration.</p>
         <p class="ai-message-hint">Configure an LLM provider in your SemPKM instance settings.</p>
       </div>
       <div id="ai-loading" class="ai-loading" hidden>
         <div class="spinner spinner-sm"></div>
         <span id="ai-loading-text" class="ai-loading-text">Analyzing page…</span>
       </div>
       <div id="ai-claims"></div>
       <div id="ai-matches"></div>
       <div id="ai-suggestions"></div>
       <div id="ai-summary"></div>
     </div>
   </div>
   ```

2. **Add DOM refs and AI state in sidebar.js.** At the top of the IIFE, alongside existing DOM refs, add:
   - `$aiInsights`, `$aiBody`, `$aiUnavailable`, `$aiLoading`, `$aiLoadingText`, `$aiClaims`, `$aiMatches`, `$aiSuggestions`, `$aiSummary`, `$aiToggle`, `$aiStatusBadge`
   - State variables: `_aiGenerationId = 0`, `_aiDismissedIris = []`
   - Wire the `#ai-toggle` button for collapsible behavior (same pattern as `_renderGroup` header click handler)

3. **Add `_initAIInsights()` function.** Called from `init()` after `fetchResults()`:
   - Increment `_aiGenerationId`
   - Show `#ai-insights`, show `#ai-loading` with text "Analyzing page..."
   - Send `{type: 'getDismissedSuggestions', url: _currentTabUrl}` to service worker — store result in `_aiDismissedIris`
   - Send `{type: 'getAIInsights'}` to service worker — capture `generationId` from response
   - Store the expected generationId for stale-check

4. **Add `chrome.runtime.onMessage` listener for `aiInsightsProgress`.** Inside the IIFE (alongside the existing `contextResultsUpdated` listener):
   - Check `message.generationId === _aiGenerationId` — discard if stale
   - Route by `message.section`:
     - `'unavailable'` → call `_renderUnavailable()`, hide loading
     - `'claims'` → call `_renderClaimsSection(message.data)`, update loading text to "Matching against your graph..."
     - `'matches'` → call `_renderMatchesSection(message.data.matches, message.data.research_gaps)`, update loading text to "Finding relationships..."
     - `'suggestions'` → filter out `_aiDismissedIris`, call `_renderSuggestionsSection(filtered)`, update loading text to "Generating summary..."
     - `'summary'` → call `_renderSummarySection(message.data)`, hide loading, update status badge with total count

5. **Implement section renderers.**

   `_renderUnavailable()`: Show `$aiUnavailable`, hide `$aiLoading`.

   `_renderClaimsSection(claims)`: Clear `$aiClaims`. If empty, return. Create a sub-group with header "Detected Claims ({count})" using the `_renderGroup` collapsible pattern. For each claim, create a card with:
   - Claim text (`.ai-claim-text`)
   - Confidence badge: `<span class="badge-confidence badge-confidence-{level}">{level}</span>` where level is `established`/`likely`/`possible`/`speculative`
   - Type badge: `<span class="badge-claim-type">{type}</span>`

   `_renderMatchesSection(matches, gaps)`: Clear `$aiMatches`. If no matches and no gaps, return. For each claim match: render claim text as header, then for each matched object: label (as link to open in SemPKM), indicator badge (`<span class="badge-indicator badge-indicator-{indicator}">{indicator}</span>` where indicator is `contradicts`/`corroborates`/`contested`/`related`), confidence level if present, type label. For research gaps: render as alert-style cards with "📋" icon, question label, and status.

   `_renderSuggestionsSection(suggestions)`: Clear `$aiSuggestions`. If empty, return. Create sub-group "Suggestions ({count})". Each suggestion card has: label text, reason (muted text), target label, Accept button (`.btn-accept`, teal accent), Dismiss button (`.btn-dismiss`, muted). Attach data attributes: `data-suggestion-type`, `data-target-iri`, `data-target-label`, `data-suggestion-index` for T03 wiring.

   `_renderSummarySection(summary)`: Clear `$aiSummary`. If empty string, return. Create a `.ai-summary-panel` div with the summary text. Simple styled text container (no markdown rendering needed for v1).

6. **Update the `init()` function.** After the existing `fetchResults(false)` call, add a call to `_initAIInsights()`. Also ensure `_currentTabUrl` and `_currentTabTitle` are set before `_initAIInsights` runs (they're set in the `chrome.tabs.query` callback — `_initAIInsights` must be called inside that callback or after a small delay to ensure tab data is available).

7. **Add CSS rules for all AI elements.** In `sidebar.css`, add comprehensive styles:

   - `.ai-section-header` — margin-top to separate from context results
   - `#ai-body` — container for all AI sub-sections
   - `.ai-message` — centered message panel (for unavailable state), using `.state-panel`-like layout
   - `.ai-loading` — inline flex with spinner and text
   - `.spinner-sm` — smaller 16px spinner variant
   - `.ai-loading-text` — 11px muted text
   - Confidence badges: `.badge-confidence` base + `.badge-confidence-established` (green: `--badge-url` vars), `.badge-confidence-likely` (blue: `--badge-title` vars), `.badge-confidence-possible` (amber: `#d97706` / `rgba(217,119,6,0.15)`), `.badge-confidence-speculative` (gray: `--badge-keyword` vars)
   - Indicator badges: `.badge-indicator` base + `.badge-indicator-contradicts` (red: `#dc2626` / `rgba(220,38,38,0.15)`), `.badge-indicator-corroborates` (green), `.badge-indicator-contested` (amber), `.badge-indicator-related` (gray)
   - `.badge-claim-type` — muted type badge
   - `.ai-claim-text` — 12px text with ellipsis overflow
   - `.ai-match-item` — nested card within match section
   - `.ai-match-label` — clickable label link (same style as `.card-label`)
   - `.ai-gap-card` — alert-style card with left amber border
   - `.ai-suggestion-card` — card with action buttons
   - `.btn-accept` — teal accent button (matching `.action-open` style)
   - `.btn-dismiss` — muted button (matching `.btn-cancel` style)
   - `.btn-accept:disabled, .btn-dismiss:disabled` — opacity 0.5 + not-allowed cursor
   - `.ai-summary-panel` — styled text container with surface background, padding, border-radius
   - `.ai-message-icon` — 24px centered icon
   - `.ai-message-text` — 12px muted text
   - `.ai-message-hint` — 11px even more muted text

8. **Verify.** Run `node --check` on sidebar.js. Grep for all rendering functions. Verify HTML has the AI container. Verify CSS has badge rules.

## Must-Haves

- [ ] `#ai-insights` container in sidebar.html with all inner section divs
- [ ] `_initAIInsights()` sends `getAIInsights` message and sets up progress listener
- [ ] Generation ID check discards stale progress messages
- [ ] `_renderClaimsSection()` renders claims with confidence badges (4 color levels)
- [ ] `_renderMatchesSection()` renders matches with indicator badges (4 indicator types) and research gaps
- [ ] `_renderSuggestionsSection()` renders suggestions with Accept/Dismiss buttons and data attributes
- [ ] `_renderSummarySection()` renders summary text in styled container
- [ ] `_renderUnavailable()` shows LLM configuration message
- [ ] Loading state shows contextual text that updates as pipeline progresses
- [ ] Dismissed IRIs filtered from suggestions before rendering
- [ ] CSS styles for all new elements: badges, indicators, suggestion buttons, summary panel, loading states
- [ ] `node --check extension/sidebar/sidebar.js` passes

## Verification

- `node --check extension/sidebar/sidebar.js` — zero errors
- `grep -c '_renderAIInsights\|_renderClaimsSection\|_renderMatchesSection\|_renderSuggestionsSection\|_renderSummarySection\|_renderUnavailable\|_initAIInsights' extension/sidebar/sidebar.js` — returns 7 or more
- `grep 'ai-insights' extension/sidebar/sidebar.html` — confirms container exists
- `grep 'badge-confidence-established\|badge-confidence-likely\|badge-confidence-possible\|badge-confidence-speculative' extension/sidebar/sidebar.css` — all 4 confidence badge colors
- `grep 'badge-indicator-contradicts\|badge-indicator-corroborates\|badge-indicator-contested\|badge-indicator-related' extension/sidebar/sidebar.css` — all 4 indicator badge colors
- `grep 'btn-accept\|btn-dismiss' extension/sidebar/sidebar.css` — suggestion action button styles

## Inputs

- `extension/sidebar/sidebar.js` (556 lines) — existing IIFE with `_showState()`, `_renderGroup()`, `_renderCard()`, `showToast()`, `renderResults()`, `fetchResults()`, `init()`. Uses `chrome.runtime.sendMessage` for service worker communication.
- `extension/sidebar/sidebar.html` (70 lines) — existing HTML with `#loading`, `#error`, `#empty`, `#results`, `#evidence-prompt` sections
- `extension/sidebar/sidebar.css` (591 lines) — dark theme CSS with existing badge styles (`.badge-url`, `.badge-title`, `.badge-keyword`), group styles (`.group-header`, `.group-body`), action button styles (`.action-open`, `.action-link`)
- T01 output: service worker sends `{type: 'aiInsightsProgress', section: 'claims'|'matches'|'suggestions'|'summary'|'unavailable', data: ..., generationId: number}` messages
- T01 output: service worker handles `getDismissedSuggestions` returning `{dismissed: [iri1, iri2, ...]}`
- S01 response schemas: DetectedClaim `{text, confidence, type}`, ClaimMatch `{claim_text, matched_objects: [{iri, label, type_iri, type_label, match_type, indicator, confidence}]}`, ResearchGap `{iri, label, question_text, status}`, RelationshipSuggestion `{type, label, target_iri, target_label, reason}`, summary is a plain string

## Observability Impact

**New signals:**
- `[SemPKM Sidebar] AI Insights: init` — logged when `_initAIInsights()` fires, includes `generationId`
- `[SemPKM Sidebar] AI Insights: progress` — logged per `aiInsightsProgress` message received, includes `section` and `generationId`
- `[SemPKM Sidebar] AI Insights: stale` — logged when a progress message is discarded due to mismatched `generationId`

**Inspection surfaces:**
- DOM: `#ai-insights` container — inspect `hidden` attribute to confirm section visibility
- DOM: `#ai-loading` + `#ai-loading-text` — verify loading state text transitions
- DOM: `#ai-unavailable` — visible when LLM not configured
- DOM: `[data-suggestion-type]`, `[data-target-iri]`, `[data-suggestion-index]` — suggestion cards carry data attributes for T03 wiring

**Failure visibility:**
- If AI pipeline fails silently, `#ai-loading` remains visible indefinitely (no timeout — T03 may add one)
- If all sections return empty, `#ai-insights` shows with only the header (no content sub-sections)
- Stale-update discards are logged but not user-visible

## Expected Output

- `extension/sidebar/sidebar.html` — expanded with `#ai-insights` container and inner section divs
- `extension/sidebar/sidebar.js` — expanded with AI state, `_initAIInsights()`, progress listener, 6 rendering functions (~300 lines added)
- `extension/sidebar/sidebar.css` — expanded with confidence badges, indicator badges, suggestion buttons, summary panel, loading states, unavailable message (~150 lines added)
