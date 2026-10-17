"""Command line: ``airlock eval``, ``airlock lint-policy``, ``airlock verify-log``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence

from . import default_policy
from .audit import verify
from .evals import MODES, SCENARIOS, results_document, run_all, to_json
from .policy import PolicyError, load_policy


def _eval(args: argparse.Namespace) -> int:
    policy = load_policy(args.policy) if args.policy else default_policy()
    scenarios = [s for s in SCENARIOS if not args.scenario or s.id in args.scenario]
    if not scenarios:
        print(f"no scenarios match {args.scenario}", file=sys.stderr)
        return 2
    results = run_all(policy, scenarios, args.mode or MODES)
    print(to_json(results) if args.format == "json" else results_document(results, scenarios), end="")
    return 0


def _lint(args: argparse.Namespace) -> int:
    try:
        policy = load_policy(args.path)
    except (OSError, PolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    warnings = policy.lint()
    for w in warnings:
        print(f"warning: {w}")
    print(f"{args.path}: {len(policy.tools)} tools, {len(warnings)} warning(s)")
    return 1 if warnings and args.strict else 0


def _verify(args: argparse.Namespace) -> int:
    key = None
    if args.key_env:
        value = os.environ.get(args.key_env)
        if not value:
            print(f"error: ${args.key_env} is not set", file=sys.stderr)
            return 2
        key = value.encode()
    result = verify(args.path, key=key)
    if result.ok:
        print(f"ok: {result.count} records, head {result.head}")
        return 0
    print(f"FAILED after {result.count} good records: {result.error}", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="airlock", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("eval", help="run the evaluation scenarios")
    p.add_argument("--policy", help="policy TOML (default: the bundled policy)")
    p.add_argument("--mode", action="append", choices=MODES, help="repeatable; default: all modes")
    p.add_argument("--scenario", action="append", help="repeatable; default: all scenarios")
    p.add_argument("--format", choices=("md", "json"), default="md")
    p.set_defaults(fn=_eval)

    p = sub.add_parser("lint-policy", help="validate a policy and warn about risky settings")
    p.add_argument("path")
    p.add_argument("--strict", action="store_true", help="exit 1 if there are warnings")
    p.set_defaults(fn=_lint)

    p = sub.add_parser("verify-log", help="check an audit log's hash chain")
    p.add_argument("path")
    p.add_argument("--key-env", help="environment variable holding the HMAC key")
    p.set_defaults(fn=_verify)

    args = parser.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
