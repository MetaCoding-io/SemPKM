---
estimated_steps: 31
estimated_files: 1
skills_used: []
---

# T03: Verify adoption metrics and visual regression check

Final verification pass. Run the adoption metric counts to confirm the slice targets are met. Start the Docker dev stack and visually verify light and dark mode on key pages. Document any intentional exemptions.

## Steps

1. **Run metric counts:**
   ```bash
   # Standalone hex (must be ≤10)
   rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l
   
   # Standalone rgba (must be ≤20)
   rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l
   
   # Non-standard breakpoints (must be zero)
   rg '@media.*max-width' frontend/static/css/ | grep -v '600\|768'
   
   # Adoption percentage
   # var_uses / (var_uses + hex + rgba) >= 0.98
   ```

2. **If counts exceed targets**, identify the remaining values, determine if they're fixable or genuine exemptions, and fix what's fixable.

3. **Start Docker dev stack** (`docker compose up -d`) and open the app in browser.

4. **Visual regression check — light mode:**
   - Workspace page: verify explorer sidebar, tab headers, editor area, panel buttons
   - Settings page: verify form inputs, section headers, status badges
   - Import page: verify status indicators, progress bars, button colors

5. **Visual regression check — dark mode:**
   - Toggle to dark mode via theme switcher
   - Verify same pages: workspace, settings, import
   - Pay special attention to: text contrast on colored backgrounds, badge colors, accent colors, overlay backgrounds, border colors

6. **Document exemptions** — add a comment block near the top of theme.css listing any intentional standalone hex/rgba values that were left unconverted and why (e.g., "FullCalendar !important overrides in views.css use theme vars but keep !important for vendor override").

## Must-Haves

- Metric counts confirmed: ≤10 hex, ≤20 rgba, 0 non-standard breakpoints
- Visual verification in both light and dark mode shows no regressions
- Any exemptions documented in theme.css

## Inputs

- `frontend/static/css/theme.css`
- `frontend/static/css/workspace.css`
- `frontend/static/css/views.css`
- `frontend/static/css/import.css`
- `frontend/static/css/vfs-browser.css`
- `frontend/static/css/copilot.css`
- `frontend/static/css/federation.css`
- `frontend/static/css/settings.css`
- `frontend/static/css/okr.css`
- `frontend/static/css/decision-matrix.css`
- `frontend/static/css/quadrant.css`
- `frontend/static/css/bmc.css`
- `frontend/static/css/style.css`
- `frontend/static/css/context-indicator.css`

## Expected Output

- `frontend/static/css/theme.css`

## Verification

rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # must be ≤10
rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # must be ≤20
rg '@media.*max-width' frontend/static/css/ | grep -v '600\|768'  # must be empty
