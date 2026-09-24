from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .baselines import MyopicBaseline, OracleBaseline
from .claim import evaluate_claim
from .domains import DOMAINS
from .packs import generated_holdout, public_pack
from .runner import run_exam
from .validation import assert_comprehensive_coverage, coverage_report, validate_scenario


def _agent(name: str):
    if name == "oracle":
        return OracleBaseline()
    if name == "myopic":
        return MyopicBaseline()
    raise SystemExit(f"unknown built-in agent: {name}")


def _print_report(report) -> None:
    payload = {
        "benchmark_version": report.benchmark_version,
        "contestant": report.contestant,
        "scenario_count": report.scenario_count,
        "per_domain": report.per_domain,
        "mandatory_pass": report.mandatory_pass,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(prog="awe", description="Agency & Wisdom Evaluation")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-domains")
    sub.add_parser("validate")

    run_public = sub.add_parser("run-public")
    run_public.add_argument("--agent", choices=["oracle", "myopic"], default="oracle")

    run_holdout = sub.add_parser("run-holdout")
    run_holdout.add_argument("--agent", choices=["oracle", "myopic"], default="myopic")
    run_holdout.add_argument("--seed", required=True)
    run_holdout.add_argument("--count", type=int, default=40)

    args = parser.parse_args()

    if args.command == "list-domains":
        for domain in DOMAINS:
            marker = "*" if domain.mandatory_for_wisdom_claim else " "
            print(f"{marker} {domain.id:24} {domain.suite:12} {domain.name}")
        return

    if args.command == "validate":
        scenarios = public_pack()
        for scenario in scenarios:
            validate_scenario(scenario)
        assert_comprehensive_coverage(scenarios)
        print(json.dumps({"ok": True, "scenarios": len(scenarios), "coverage": coverage_report(scenarios)}, indent=2))
        return

    if args.command == "run-public":
        report = run_exam(_agent(args.agent), public_pack())
        _print_report(report)
        return

    if args.command == "run-holdout":
        report = run_exam(_agent(args.agent), generated_holdout(args.seed, args.count))
        _print_report(report)
        return


if __name__ == "__main__":
    main()
