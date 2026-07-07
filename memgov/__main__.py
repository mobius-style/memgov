"""memgov CLI.

    memgov init                     scaffold memgov.toml + SHARED_STATE.md
    memgov scan [--summary]         cross-store drift scan (CONFLICT_MAP)
    memgov fresh [--summary]        freshness check on status-bearing files
    memgov hook-context             SessionStart JSON for Claude Code / Codex
    memgov mark-restored <store>    record a reconciliation pass

All commands accept --config <path> (default: ./memgov.toml if present).
`hook-context` prints a hookSpecificOutput JSON block — the same schema is
accepted by both Claude Code and Codex SessionStart hooks.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, config as config_mod, freshness, scan as scan_mod

TEMPLATES = Path(__file__).resolve().parent / "templates"


def _cfg(args: argparse.Namespace) -> config_mod.Config:
    return config_mod.load(args.config)


def cmd_init(args: argparse.Namespace) -> int:
    wrote = []
    for name in ("memgov.toml", "SHARED_STATE.md"):
        dest = Path(name)
        if dest.exists():
            print(f"skip (exists): {dest}")
            continue
        dest.write_text((TEMPLATES / name).read_text(encoding="utf-8"),
                        encoding="utf-8")
        wrote.append(str(dest))
    print("scaffolded:", ", ".join(wrote) if wrote else "(nothing)")
    print("next: edit memgov.toml [stores] and add SHARED_STATE.md rows, "
          "then wire adapters/ into your agents' SessionStart hooks.")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    result = scan_mod.scan(cfg)
    scan_mod.write_outputs(cfg, result)
    if args.summary:
        line = scan_mod.summary_line(cfg, result)
        if line:
            print(line)
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_fresh(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    hits = freshness.check(cfg)
    if args.summary:
        if hits:
            print(f"memory-restore due: {len(hits)} status-bearing file(s) "
                  "possibly stale:")
            for h in hits[:10]:
                print(f"  - {h['store']}/{h['file']} "
                      f"(last touched {h['age_days']}d ago)")
            if len(hits) > 10:
                print(f"  ... {len(hits) - 10} more")
        return 0
    print(json.dumps(hits, ensure_ascii=False, indent=2))
    return 0


def cmd_hook_context(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    sections: list[str] = []
    if cfg.inject_shared_state and cfg.shared_state.exists():
        sections += ["# SHARED_STATE (cross-agent live state)", "",
                     cfg.shared_state.read_text(
                         encoding="utf-8")[: cfg.max_inject_chars], ""]
    hits = freshness.check(cfg)
    if hits:
        sections.append(
            f"memory-restore due: {len(hits)} status-bearing memory file(s) "
            "possibly stale — verify against primary sources before relying "
            "on them:")
        sections += [f"  - {h['store']}/{h['file']} ({h['age_days']}d)"
                     for h in hits[:10]]
        sections.append("")
    result = scan_mod.scan(cfg)
    scan_mod.write_outputs(cfg, result)
    line = scan_mod.summary_line(cfg, result)
    if line:
        sections.append(line)
    context = "\n".join(sections).strip()
    if not context:
        print("{}")
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": context + "\n",
    }}, ensure_ascii=False))
    return 0


def cmd_mark_restored(args: argparse.Namespace) -> int:
    cfg = _cfg(args)
    if args.store not in cfg.stores:
        print(f"unknown store {args.store!r}; known: "
              f"{', '.join(sorted(cfg.stores))}", file=sys.stderr)
        return 2
    marker = freshness.mark_restored(cfg, args.store)
    print(f"marked: {marker}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="memgov",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("--version", action="version", version=__version__)
    ap.add_argument("--config", default=None,
                    help="path to memgov.toml (default: ./memgov.toml)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="scaffold config + SHARED_STATE templates")
    for name, help_ in (("scan", "cross-store drift scan"),
                        ("fresh", "freshness check")):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--summary", action="store_true")
    sub.add_parser("hook-context",
                   help="SessionStart JSON for Claude Code / Codex hooks")
    sp = sub.add_parser("mark-restored", help="record a reconciliation pass")
    sp.add_argument("store")
    args = ap.parse_args(argv)
    return {"init": cmd_init, "scan": cmd_scan, "fresh": cmd_fresh,
            "hook-context": cmd_hook_context,
            "mark-restored": cmd_mark_restored}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
