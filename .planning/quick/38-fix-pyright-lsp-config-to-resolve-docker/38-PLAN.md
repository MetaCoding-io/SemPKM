---
phase: quick-38
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyrightconfig.json
autonomous: true
must_haves:
  truths:
    - "Pyright running from project root resolves all backend Python imports without false positives"
    - "LSP diagnostics in Claude Code show no reportMissingImports for installed packages"
  artifacts:
    - path: "pyrightconfig.json"
      provides: "Root-level Pyright config pointing to backend venv"
  key_links:
    - from: "pyrightconfig.json"
      to: "backend/.venv"
      via: "venvPath + venv settings"
      pattern: "venvPath.*backend"
---

<objective>
Create a root-level pyrightconfig.json so that Pyright (and Claude Code's LSP) resolves
Python imports correctly when running from the project root.

Purpose: Eliminate false-positive "reportMissingImports" diagnostics for all third-party
packages (fastapi, httpx, pydantic, rdflib, etc.) that are installed in backend/.venv.

Output: A single pyrightconfig.json at the repository root.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/pyrightconfig.json (existing backend-local config)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create root-level pyrightconfig.json</name>
  <files>pyrightconfig.json</files>
  <action>
Create `pyrightconfig.json` at the repository root (`/home/james/Code/SemPKM/pyrightconfig.json`)
with the following configuration:

```json
{
  "venvPath": "./backend",
  "venv": ".venv",
  "include": ["backend/app"],
  "pythonVersion": "3.14"
}
```

Key settings:
- `venvPath` + `venv`: Together resolve to `backend/.venv` — the uv-managed virtualenv
  containing all installed dependencies (fastapi, httpx, pydantic, rdflib, etc.)
- `include`: Scopes analysis to `backend/app` only (the actual Python source tree).
  Avoids analyzing venv internals, migrations, or other non-app Python files.
- `pythonVersion`: Matches the Python 3.14 interpreter in the venv.

Do NOT remove the existing `backend/pyrightconfig.json` — it allows Pyright to also
work when run directly from the `backend/` directory (backward compatibility).
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python3 -c "import json; c=json.load(open('pyrightconfig.json')); assert c['venvPath']=='./backend'; assert c['venv']=='.venv'; assert 'backend/app' in c['include']; assert c['pythonVersion']=='3.14'; print('Config valid')"</automated>
  </verify>
  <done>
Root-level pyrightconfig.json exists with correct venvPath, venv, include, and pythonVersion
settings. Pyright running from the project root can locate backend/.venv and resolves all
third-party imports without false reportMissingImports diagnostics.
  </done>
</task>

</tasks>

<verification>
1. `pyrightconfig.json` exists at repository root with correct settings
2. `backend/pyrightconfig.json` still exists (backward compatibility)
3. Pyright from root resolves imports: `cd /home/james/Code/SemPKM && npx pyright backend/app/main.py --outputjson 2>/dev/null | jq '.generalDiagnostics | length'` should show no reportMissingImports errors for installed packages
</verification>

<success_criteria>
- Root pyrightconfig.json created with venvPath=./backend, venv=.venv, include=[backend/app], pythonVersion=3.14
- Claude Code LSP no longer reports false-positive missing import diagnostics for backend Python files
</success_criteria>

<output>
After completion, create `.planning/quick/38-fix-pyright-lsp-config-to-resolve-docker/38-SUMMARY.md`
</output>
