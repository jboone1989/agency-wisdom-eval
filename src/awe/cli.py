from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess

from .adapters.apollo_scheming import run_apollo_insider_trading_reproduction
from .adapters.jsonl import JsonLineSubprocessAgent
from .adapters.machiavelli import run_machiavelli
from .adapters.sotopia import run_sotopia_benchmark
from .baselines import MyopicBaseline, OracleBaseline
from .domains import DOMAINS
from .external import (
    EXTERNAL_BENCHMARKS,
    build_external_evidence,
    evidence_from_json,
    evidence_to_json,
    get_external_benchmark,
    sha256_file,
    validate_external_evidence,
)
from .packs import generated_holdout, public_pack
from .runner import pack_hash, run_exam
from .upstream import get_upstream_runner_plan
from .upstream_contracts import (
    verify_apollo_insider_checkout,
    verify_machiavelli_checkout,
    verify_metr_task_standard_checkout,
    verify_osworld_checkout,
    verify_sotopia_checkout,
)
from .validation import assert_comprehensive_coverage, coverage_report, validate_scenario


def _agent(name: str):
    if name == "oracle":
        return OracleBaseline()
    if name == "myopic":
        return MyopicBaseline()
    raise SystemExit(f"unknown built-in agent: {name}")


def _report_payload(report, *, include_traces: bool = False) -> dict:
    payload = {
        "benchmark_version": report.benchmark_version,
        "contestant": report.contestant,
        "scenario_count": report.scenario_count,
        "per_domain": report.per_domain,
        "opportunities": report.opportunities,
        "mandatory_pass": report.mandatory_pass,
        "metadata": report.metadata,
    }
    if include_traces:
        payload["traces"] = [asdict(item) for item in report.traces]
    return payload


def _emit(report, *, output: str | None = None, include_traces: bool = False) -> None:
    payload = _report_payload(report, include_traces=include_traces)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


def _pack(name: str, *, seed: str | None, count: int) -> list:
    if name == "public":
        return public_pack()
    if name == "holdout":
        if not seed:
            raise SystemExit("--seed is required for holdout")
        return generated_holdout(seed, count)
    raise SystemExit(f"unknown pack: {name}")


def _parse_metrics(values: list[str]) -> dict[str, object]:
    metrics: dict[str, object] = {}
    for item in values:
        if "=" not in item:
            raise SystemExit(f"invalid --metric {item!r}; expected KEY=VALUE")
        key, raw = item.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit("metric key must not be empty")
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        metrics[key] = value
    return metrics


def _contestant_command(raw: list[str]) -> list[str]:
    command = list(raw)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise SystemExit("contestant command is required after --")
    return command


def _external_record(args) -> int:
    evidence = build_external_evidence(
        benchmark_id=args.benchmark,
        benchmark_version=args.benchmark_version,
        source_revision=args.source_revision,
        contestant=args.contestant,
        run_id=args.run_id,
        artifact=args.artifact,
        metrics=_parse_metrics(args.metric),
        metadata={
            "runner_command": list(args.runner_command or []),
            "runner_cwd": args.runner_cwd,
        },
    )
    rendered = evidence_to_json(evidence)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


def _external_run(args) -> int:
    command = _contestant_command(args.runner_command)
    completed = subprocess.run(
        command,
        cwd=args.runner_cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=args.timeout_seconds,
        check=False,
        text=True,
    )
    receipt = {
        "benchmark": args.benchmark,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-12000:],
        "stderr_tail": completed.stderr[-12000:],
        "command": command,
        "cwd": args.runner_cwd,
    }
    if completed.returncode != 0:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return completed.returncode or 1
    if not Path(args.artifact).is_file():
        receipt["error"] = "runner succeeded but expected artifact is missing"
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
        return 2
    args.runner_command = command
    _external_record(args)
    return 0


def _external_doctor(args) -> int:
    checks = []
    if args.machiavelli:
        checks.append(verify_machiavelli_checkout(args.machiavelli))
    if args.sotopia:
        checks.append(verify_sotopia_checkout(args.sotopia))
    if args.osworld:
        checks.append(verify_osworld_checkout(args.osworld))
    if args.metr_task_standard:
        checks.append(verify_metr_task_standard_checkout(args.metr_task_standard))
    if args.apollo:
        checks.append(verify_apollo_insider_checkout(args.apollo))
    if not checks:
        raise SystemExit("provide at least one upstream checkout path")
    payload = {"ok": all(item.ok for item in checks), "checks": [asdict(item) for item in checks]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


def main() -> None:
    parser = argparse.ArgumentParser(prog="awe", description="Agency & Wisdom Evaluation")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-domains")
    sub.add_parser("validate")

    external_list = sub.add_parser("external-list")
    external_list.add_argument("--mode", choices=["official", "gated", "reproduction"])

    external_show = sub.add_parser("external-show")
    external_show.add_argument("benchmark", choices=[spec.id for spec in EXTERNAL_BENCHMARKS])

    external_plan = sub.add_parser("external-plan")
    external_plan.add_argument("benchmark", choices=[spec.id for spec in EXTERNAL_BENCHMARKS])

    external_verify = sub.add_parser("external-verify")
    external_verify.add_argument("evidence")

    doctor = sub.add_parser("external-doctor")
    doctor.add_argument("--machiavelli")
    doctor.add_argument("--sotopia")
    doctor.add_argument("--osworld")
    doctor.add_argument("--metr-task-standard", dest="metr_task_standard")
    doctor.add_argument("--apollo")

    for name in ("external-record", "external-run"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--benchmark", required=True, choices=[spec.id for spec in EXTERNAL_BENCHMARKS])
        cmd.add_argument("--benchmark-version", required=True)
        cmd.add_argument("--source-revision", required=True)
        cmd.add_argument("--contestant", required=True)
        cmd.add_argument("--run-id", required=True)
        cmd.add_argument("--artifact", required=True)
        cmd.add_argument("--output", required=True)
        cmd.add_argument("--metric", action="append", default=[])
        cmd.add_argument("--runner-cwd")
        if name == "external-run":
            cmd.add_argument("--timeout-seconds", type=float, default=None)
            cmd.add_argument("runner_command", nargs=argparse.REMAINDER)
        else:
            cmd.set_defaults(runner_command=[])

    mach = sub.add_parser("run-machiavelli")
    mach.add_argument("--traj-dir", required=True)
    mach.add_argument("--game", action="append", default=[])
    mach.add_argument("--num-episodes", type=int, default=1)
    mach.add_argument("--max-traj-length", type=int, default=1000)
    mach.add_argument("contestant_command", nargs=argparse.REMAINDER)

    sotopia = sub.add_parser("run-sotopia")
    sotopia.add_argument("--partner-model", required=True)
    sotopia.add_argument("--evaluator-model", required=True)
    sotopia.add_argument("--batch-size", type=int, default=10)
    sotopia.add_argument("--task", default="hard")
    sotopia.add_argument("--url", default="")
    sotopia.add_argument("--save-dir", required=True)
    sotopia.add_argument("--tag", default="")
    sotopia.add_argument("--timeout-seconds", type=float, default=90.0)
    sotopia.add_argument("contestant_command", nargs=argparse.REMAINDER)

    apollo = sub.add_parser("run-apollo-reproduction")
    apollo.add_argument("--prompt", required=True)
    apollo.add_argument("--artifact", required=True)
    apollo.add_argument("contestant_command", nargs=argparse.REMAINDER)

    run_public = sub.add_parser("run-public")
    run_public.add_argument("--agent", choices=["oracle", "myopic"], default="oracle")
    run_public.add_argument("--output")
    run_public.add_argument("--include-traces", action="store_true")

    run_holdout = sub.add_parser("run-holdout")
    run_holdout.add_argument("--agent", choices=["oracle", "myopic"], default="myopic")
    run_holdout.add_argument("--seed", required=True)
    run_holdout.add_argument("--count", type=int, default=40)
    run_holdout.add_argument("--output")
    run_holdout.add_argument("--include-traces", action="store_true")

    run_command = sub.add_parser("run-command")
    run_command.add_argument("--name", required=True)
    run_command.add_argument("--pack", choices=["public", "holdout"], default="public")
    run_command.add_argument("--seed")
    run_command.add_argument("--count", type=int, default=40)
    run_command.add_argument("--timeout-seconds", type=float, default=45.0)
    run_command.add_argument("--start-index", type=int, default=0)
    run_command.add_argument("--limit", type=int)
    run_command.add_argument("--journal")
    run_command.add_argument("--output")
    run_command.add_argument("--include-traces", action="store_true")
    run_command.add_argument("contestant_command", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    if args.command == "list-domains":
        for domain in DOMAINS:
            marker = "*" if domain.mandatory_for_wisdom_claim else " "
            print(f"{marker} {domain.id:24} {domain.suite:12} {domain.name}")
        return

    if args.command == "external-list":
        rows = [
            {
                "id": spec.id,
                "name": spec.name,
                "mode": spec.mode.value,
                "repository": spec.repository,
                "domains": list(spec.domains),
            }
            for spec in EXTERNAL_BENCHMARKS
            if args.mode is None or spec.mode.value == args.mode
        ]
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if args.command == "external-show":
        print(json.dumps(asdict(get_external_benchmark(args.benchmark)), ensure_ascii=False, indent=2))
        return

    if args.command == "external-plan":
        print(json.dumps(asdict(get_upstream_runner_plan(args.benchmark)), ensure_ascii=False, indent=2))
        return

    if args.command == "external-doctor":
        raise SystemExit(_external_doctor(args))

    if args.command == "external-verify":
        evidence = evidence_from_json(args.evidence)
        reasons = list(validate_external_evidence(evidence))
        artifact = evidence.metadata.get("artifact_path")
        if artifact and Path(str(artifact)).is_file():
            if sha256_file(str(artifact)) != evidence.artifact_sha256:
                reasons.append("artifact hash mismatch")
        print(json.dumps({"ok": not reasons, "reasons": reasons, "evidence": asdict(evidence)}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if not reasons else 1)

    if args.command == "external-record":
        raise SystemExit(_external_record(args))

    if args.command == "external-run":
        raise SystemExit(_external_run(args))

    if args.command == "run-machiavelli":
        outputs = run_machiavelli(
            _contestant_command(args.contestant_command),
            traj_dir=args.traj_dir,
            games=args.game or None,
            num_episodes=args.num_episodes,
            max_traj_length=args.max_traj_length,
        )
        print(json.dumps({"ok": True, "trajectories": [str(path) for path in outputs]}, indent=2))
        return

    if args.command == "run-sotopia":
        run_sotopia_benchmark(
            _contestant_command(args.contestant_command),
            partner_model=args.partner_model,
            evaluator_model=args.evaluator_model,
            batch_size=args.batch_size,
            task=args.task,
            url=args.url,
            save_dir=args.save_dir,
            tag=args.tag,
            timeout_seconds=args.timeout_seconds,
        )
        return

    if args.command == "run-apollo-reproduction":
        result = run_apollo_insider_trading_reproduction(
            _contestant_command(args.contestant_command),
            prompt_path=args.prompt,
            artifact_path=args.artifact,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
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
        _emit(report, output=args.output, include_traces=args.include_traces)
        return

    if args.command == "run-holdout":
        report = run_exam(_agent(args.agent), generated_holdout(args.seed, args.count))
        _emit(report, output=args.output, include_traces=args.include_traces)
        return

    if args.command == "run-command":
        command = _contestant_command(args.contestant_command)
        full_scenarios = _pack(args.pack, seed=args.seed, count=args.count)
        start = max(0, int(args.start_index))
        stop = len(full_scenarios) if args.limit is None else min(
            len(full_scenarios), start + max(0, int(args.limit))
        )
        scenarios = full_scenarios[start:stop]
        if not scenarios:
            raise SystemExit("selected scenario slice is empty")

        journal_path = Path(args.journal) if args.journal else None
        if journal_path is not None:
            journal_path.parent.mkdir(parents=True, exist_ok=True)

        def journal(result):
            if journal_path is None:
                return
            with journal_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(result), ensure_ascii=False, default=str) + "\n")
                handle.flush()

        with JsonLineSubprocessAgent(
            command,
            name=args.name,
            timeout_seconds=args.timeout_seconds,
        ) as agent:
            report = run_exam(agent, scenarios, on_result=journal)
        report.metadata.update({
            "pack": args.pack,
            "full_pack_sha256": pack_hash(full_scenarios),
            "slice_start_index": start,
            "slice_stop_index": stop,
            "holdout_seed_hash_exposed_to_report": False,
            "contestant_command": command,
        })
        _emit(report, output=args.output, include_traces=args.include_traces)
        return


if __name__ == "__main__":
    main()
