"""repolens command line.

    python -m tools.repolens scan     # facts only, no model
    python -m tools.repolens build    # facts + model + page
    python -m tools.repolens check    # run checks, exit 1 on failure  (hooks/CI)
    python -m tools.repolens stages   # list registered stages

`check` is what a pre-commit hook and CI both call, so there is one
implementation of "is this repo still what it claims to be".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .pipeline import Context, PipelineError, REGISTRY, run
from . import stages  # noqa: F401  (registers everything)

DEFAULT_CONFIG = ".repolens.yml"


def load_config(root: Path, path: str | None) -> dict:
    p = root / (path or DEFAULT_CONFIG)
    if not p.exists():
        raise SystemExit(f"no config at {p}. Write one, or pass --config.")
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def build_context(args) -> Context:
    root = Path(args.root).resolve()
    cfg = load_config(root, args.config)
    return Context(root=root, config=cfg, verbose=args.verbose)


def pipeline_for(cfg: dict, command: str) -> list[str]:
    pipes = cfg.get("pipelines") or {}
    if command in pipes:
        return pipes[command]
    return cfg.get("pipeline") or list(REGISTRY)


def cmd_run(args, command: str) -> int:
    ctx = build_context(args)
    order = pipeline_for(ctx.config, command)
    print(f"repolens {command} — {ctx.root}")
    try:
        run(ctx, order, only=args.only, skip=args.skip)
    except PipelineError as e:
        print(f"\npipeline error: {e}", file=sys.stderr)
        return 2

    total = sum(ctx.timings.values())
    slow = sorted(ctx.timings.items(), key=lambda kv: -kv[1])[:3]
    print(f"\ndone in {total} ms  (slowest: " +
          ", ".join(f"{k} {v}ms" for k, v in slow) + ")")

    warns = [l for l in ctx.logs if l.startswith("WARNING")]
    if warns:
        print(f"{len(warns)} warning(s)")

    if command == "check":
        return report_checks(ctx, args)
    return 0


def baseline_path(ctx: Context) -> Path:
    return ctx.root / ctx.config.get("out_dir", ".repolens") / "baseline.json"


def load_baseline(ctx: Context) -> dict:
    p = baseline_path(ctx)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("checks", {})


def regressions(results: list[dict], base: dict) -> list[dict]:
    """Only things that got worse.

    A checker introduced to an existing codebase that blocks on pre-existing
    findings gets switched off within a day. Fail on the delta instead: a check
    that used to pass and now fails, or one whose count went up.
    """
    out = []
    for r in results:
        if r["passed"]:
            continue
        b = base.get(r["id"])
        if b is None:                       # never recorded — treat as new
            out.append({**r, "why": "new check, not in baseline"})
        elif b.get("passed"):
            out.append({**r, "why": "was passing, now fails"})
        else:
            was, now = b.get("actual"), r.get("actual")
            if isinstance(was, int) and isinstance(now, int) and now > was:
                out.append({**r, "why": f"got worse: {was} → {now}"})
    return out


def report_checks(ctx: Context, args) -> int:
    results = ctx.facts.get("checks", [])
    failed = [r for r in results if not r["passed"]]
    order = {"high": 0, "medium": 1, "low": 2, "note": 3}
    failed.sort(key=lambda r: order.get(r["severity"], 9))

    print()
    for r in failed:
        print(f"  [{r['severity'].upper():<6}] {r['title']}")
        if r.get("evidence"):
            print(f"           {r['evidence']}")
    if not failed:
        print(f"  all {len(results)} checks pass")

    if args.json:
        print(json.dumps(results, indent=2))

    base = load_baseline(ctx)
    if args.strict or not base:
        blocking = [r for r in failed if r["severity"] in (args.fail_on or [])]
        if not base and failed:
            print("\n  (no baseline recorded — run `repolens baseline` to accept "
                  "these as known and block only on regressions)")
    else:
        regs = [r for r in regressions(results, base)
                if r["severity"] in (args.fail_on or [])]
        blocking = regs
        if regs:
            print(f"\n  {len(regs)} REGRESSION(S) against the baseline:")
            for r in regs:
                print(f"    {r['title']} — {r['why']}")
        else:
            print(f"\n  no regressions ({len(failed)} known finding(s) held at baseline)")

    return 1 if blocking else 0


def cmd_baseline(args) -> int:
    ctx = build_context(args)
    run(ctx, pipeline_for(ctx.config, "check"))
    snapshot = {
        r["id"]: {"passed": r["passed"], "actual": r.get("actual"),
                  "severity": r["severity"]}
        for r in ctx.facts.get("checks", [])
    }
    p = baseline_path(ctx)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"checks": snapshot}, indent=2, sort_keys=True), encoding="utf-8")
    failing = sum(1 for v in snapshot.values() if not v["passed"])
    print(f"\nbaseline written: {len(snapshot)} checks, {failing} currently failing")
    print("future runs block only on regressions against this.")
    return 0


def cmd_stages(args) -> int:
    print(f"{len(REGISTRY)} registered stages\n")
    for sid, st in REGISTRY.items():
        req = ", ".join(st.requires) or "—"
        print(f"  {sid:<14} {st.doc}")
        print(f"  {'':<14} requires: {req}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="repolens")
    ap.add_argument("command", choices=["scan", "build", "check", "baseline", "stages"])
    ap.add_argument("--root", default=".")
    ap.add_argument("--config", default=None)
    ap.add_argument("--only", nargs="*", help="run only these stages")
    ap.add_argument("--skip", nargs="*", help="skip these stages")
    ap.add_argument("--json", action="store_true", help="dump check results as JSON")
    ap.add_argument("--fail-on", nargs="*", default=["high"],
                    help="severities that make `check` exit non-zero")
    ap.add_argument("--strict", action="store_true",
                    help="fail on every finding, not just regressions")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    if args.command == "stages":
        return cmd_stages(args)
    if args.command == "baseline":
        return cmd_baseline(args)
    return cmd_run(args, args.command)


if __name__ == "__main__":
    raise SystemExit(main())
