---
parallel:
  enabled: false
  max_workers: 2            # Concurrent workers (1-4, default: 2)
  budget_ceiling: 50.00     # Aggregate cost limit in dollars (optional)
  merge_strategy: "per-milestone"  # When to merge: "per-slice" or "per-milestone"
  auto_merge: "confirm"            # "auto", "confirm", or "manual"
# git:
#   isolation: "none"        # Work directly on current branch — no worktrees, no milestone branches
---
