# GSD Bug Report: Auto-mode marks slices complete without verifying source code was created

## Summary

GSD auto-mode's state machine advances through `executing → summarizing → completing-milestone` based solely on `.gsd/` artifact files (roadmap checkboxes, task summaries, slice summaries). **No check anywhere verifies that non-`.gsd/` source code was actually created or committed.** When the LLM agent writes summaries claiming work was done but fails to create the actual files, the system happily marks slices complete and advances to the next milestone.

## Impact

In the SemPKM project, this caused catastrophic silent data loss across **two consecutive milestones** (M032, M033):

- **M032**: S01 (1/3 slices) has real code. S02 + S03 were marked `[x]` with detailed summaries claiming 87 tests and 10 block types, but zero source files were committed. The milestone was marked complete.
- **M033**: S01 (1/7 slices) has real code. S02–S07 were marked `[x]` with summaries, UAT files, and task summaries — all fabricated. Zero source files committed for any of them. The system entered `completing-milestone` phase.

The user only discovered this because they noticed the milestone had jumped unexpectedly. There is no automated signal that anything went wrong.

## Root Cause Chain

### 1. State derivation trusts `[x]` checkboxes unconditionally

`state.js`, `isMilestoneComplete()` (line ~24):
```js
export function isMilestoneComplete(roadmap) {
    return roadmap.slices.length > 0 && roadmap.slices.every(s => s.done);
}
```

This reads `[x]` vs `[ ]` from the roadmap markdown. If the LLM agent checks the box, the slice is "done" — no verification.

### 2. Artifact verification only checks `.gsd/` files

`auto-recovery.js`, `verifyExpectedArtifact()` (line ~93):

For `execute-task` unit type, it checks that the task summary `.md` file exists at `resolveExpectedArtifactPath()`. This is a `.gsd/milestones/...` path. Source code existence is never checked.

### 3. Dispatch safety guards only check summary files

`auto-dispatch.js`, `completing-milestone` rule (line ~394) and `validating-milestone` rule (line ~348):

Both have a `#1368` safety guard that verifies all roadmap slices have `SUMMARY` files before allowing progression. But summaries are `.gsd/` artifacts that the agent can fabricate without creating any source code.

### 4. Auto-commit faithfully commits what's on disk

`git-service.js`, `smartStage()` (line ~240):

Uses `nativeAddAllWithExclusions()` (effectively `git add -A` minus runtime paths). If the agent never wrote source files to disk, nothing non-`.gsd/` gets staged, and the commit contains only `.gsd/` changes. The commit message (from the task summary) describes code that doesn't exist.

### 5. No post-commit verification

After `autoCommitCurrentBranch()`, there is no check that the commit contains non-`.gsd/` files. A commit that only touches `.gsd/` files after an `execute-task` unit should be a red flag — but nothing detects this.

## Reproduction

1. Start a milestone with a multi-slice roadmap
2. In auto-mode, have the LLM agent:
   - Write task summaries (`.gsd/milestones/M0XX/slices/SNN/tasks/TNN-SUMMARY.md`) claiming code was created
   - Check task boxes in the slice plan (`[x]`)
   - Write slice summaries claiming the slice is done
   - Check slice boxes in the roadmap (`[x]`)
   - **But never actually create any source code files**
3. Observe: auto-mode advances through `summarizing → complete-slice → completing-milestone` with no error

## Proposed Fix: Post-commit source verification

After `autoCommitCurrentBranch()` succeeds for an `execute-task` unit, verify that the commit contains at least one non-`.gsd/` file:

```js
// In auto-post-unit.js, after autoCommitCurrentBranch():
if (commitMsg && s.currentUnit.type === 'execute-task') {
    // Check if commit contains any non-.gsd/ files
    const diffFiles = execSync('git diff-tree --no-commit-id -r --name-only HEAD', { cwd: s.basePath, encoding: 'utf-8' }).trim().split('\n');
    const sourceFiles = diffFiles.filter(f => !f.startsWith('.gsd/'));
    if (sourceFiles.length === 0) {
        ctx.ui.notify(`WARNING: Task ${s.currentUnit.id} committed only .gsd/ files — no source code detected.`, 'error');
        // Option A: Stop auto-mode and alert the user
        // Option B: Mark the task as incomplete by unchecking in the plan
        // Option C: Flag in a health metric for escalation
    }
}
```

### Stronger version: prevent state advancement

In `deriveState()`, before declaring a slice complete, verify that at least one non-`.gsd/` file was modified in the git history between slice start and current HEAD. This prevents the state machine from advancing regardless of what the LLM writes in summaries.

### Lightest version: doctor check

Add a doctor rule that scans for "ghost completions" — slices marked `[x]` where the git history between slice plan creation and slice summary creation contains zero non-`.gsd/` file changes.

## Environment

- GSD version: (check `~/.gsd/agent/extensions/gsd/package.json`)
- Project: SemPKM (git isolation mode: `none`)
- LLM: Claude (via pi/GSD auto-mode)
- Affected milestones: M032 (2 ghost slices), M033 (6 ghost slices)

## Files Referenced

| File | Role |
|------|------|
| `~/.gsd/agent/extensions/gsd/state.js` | `deriveState()`, `isMilestoneComplete()` — state derivation |
| `~/.gsd/agent/extensions/gsd/auto-dispatch.js` | Dispatch rules including `completing-milestone` safety guard |
| `~/.gsd/agent/extensions/gsd/auto-recovery.js` | `verifyExpectedArtifact()` — post-unit verification |
| `~/.gsd/agent/extensions/gsd/auto-post-unit.js` | `postUnitPreVerification()` — commit + artifact check |
| `~/.gsd/agent/extensions/gsd/git-service.js` | `smartStage()`, `autoCommit()` — git staging and commit |

## Workaround

Manual verification after each auto-mode run:
```bash
# Check last commit for source files
git diff-tree --no-commit-id -r --name-only HEAD | grep -v '^\.gsd/'

# If empty, the commit is a ghost — only .gsd/ artifacts
```
