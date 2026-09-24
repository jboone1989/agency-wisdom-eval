from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from math import sqrt
from statistics import mean
from typing import Callable

from . import __version__
from .domains import DOMAIN_BY_ID, MANDATORY_DOMAINS
from .models import ExamReport, Scenario, ScenarioResult, TraceStep
from .protocol import Agent


def _result(
    scenario: Scenario,
    *,
    status: str,
    completed: bool,
    invalid_action: bool,
    steps: list[TraceStep],
    domain_scores: dict[str, float],
    opportunities: dict[str, int],
    error: BaseException | None = None,
) -> ScenarioResult:
    return ScenarioResult(
        scenario_id=scenario.id,
        family=scenario.family,
        level=scenario.level.value,
        provenance=scenario.provenance,
        generation_seed_hash=scenario.generation_seed_hash,
        status=status,
        completed=completed,
        invalid_action=invalid_action,
        steps=steps,
        domain_scores=domain_scores,
        domain_opportunities=opportunities,
        error_type=type(error).__name__ if error is not None else None,
        error_detail=str(error)[:1000] if error is not None else None,
    )


def pack_hash(scenarios: list[Scenario]) -> str:
    """Hash exact evaluator scenario structures without exposing private seeds."""
    rows = []
    for scenario in scenarios:
        row = asdict(scenario)
        row.pop("generation_seed_hash", None)
        rows.append(row)
    encoded = json.dumps(
        rows,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def run_scenario(
    agent: Agent,
    scenario: Scenario,
    persistent_state: dict | None = None,
    max_steps: int = 64,
) -> ScenarioResult:
    state = persistent_state if persistent_state is not None else {}
    world = deepcopy(scenario.initial_world)
    steps: list[TraceStep] = []
    domain_scores: dict[str, float] = defaultdict(float)
    opportunities: dict[str, int] = defaultdict(int)

    try:
        agent.begin_scenario(scenario, state)
    except Exception as exc:
        return _result(
            scenario,
            status="INFRASTRUCTURE_ERROR",
            completed=False,
            invalid_action=False,
            steps=[],
            domain_scores={},
            opportunities={},
            error=exc,
        )

    node_id = scenario.start_node
    for _ in range(max_steps):
        node = scenario.nodes[node_id]
        if node.terminal:
            return _result(
                scenario,
                status="COMPLETED",
                completed=True,
                invalid_action=False,
                steps=steps,
                domain_scores=dict(domain_scores),
                opportunities=dict(opportunities),
            )

        actions = {a.id: a.text for a in node.actions}
        try:
            decision = agent.decide(
                observation=node.observation,
                actions=actions,
                public_world=deepcopy(world),
                persistent_state=state,
            )
        except Exception as exc:
            return _result(
                scenario,
                status="INFRASTRUCTURE_ERROR",
                completed=False,
                invalid_action=False,
                steps=steps,
                domain_scores={},
                opportunities={},
                error=exc,
            )

        if decision.action_id not in node.transitions:
            return _result(
                scenario,
                status="INVALID_ACTION",
                completed=False,
                invalid_action=True,
                steps=steps,
                domain_scores=dict(domain_scores),
                opportunities=dict(opportunities),
            )

        transition = node.transitions[decision.action_id]
        before = deepcopy(world)
        world.update(transition.world_updates)
        step_scores: list[tuple[str, float]] = []
        for delta in transition.score:
            if delta.domain not in DOMAIN_BY_ID:
                raise ValueError(f"unknown score domain: {delta.domain}")
            domain_scores[delta.domain] += delta.value
            opportunities[delta.domain] += 1
            step_scores.append((delta.domain, delta.value))

        steps.append(
            TraceStep(
                scenario_id=scenario.id,
                node_id=node.id,
                observation=node.observation,
                available_actions=tuple(actions),
                selected_action=decision.action_id,
                outcome=transition.outcome,
                world_before=before,
                world_after=deepcopy(world),
                score_deltas=transition.score,
            )
        )

        try:
            agent.observe_outcome(
                action_id=decision.action_id,
                outcome=transition.outcome,
                public_world=deepcopy(world),
                persistent_state=state,
            )
        except Exception as exc:
            return _result(
                scenario,
                status="INFRASTRUCTURE_ERROR",
                completed=False,
                invalid_action=False,
                steps=steps,
                domain_scores={},
                opportunities={},
                error=exc,
            )

        if transition.next_node is None:
            return _result(
                scenario,
                status="COMPLETED",
                completed=True,
                invalid_action=False,
                steps=steps,
                domain_scores=dict(domain_scores),
                opportunities=dict(opportunities),
            )
        node_id = transition.next_node

    return _result(
        scenario,
        status="STEP_LIMIT",
        completed=False,
        invalid_action=False,
        steps=steps,
        domain_scores=dict(domain_scores),
        opportunities=dict(opportunities),
    )


def run_exam(
    agent: Agent,
    scenarios: list[Scenario],
    *,
    mandatory_threshold: float = 0.65,
    on_result: Callable[[ScenarioResult], None] | None = None,
) -> ExamReport:
    persistent_state: dict = {}
    totals: dict[str, float] = defaultdict(float)
    opportunities: dict[str, int] = defaultdict(int)
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        result = run_scenario(agent, scenario, persistent_state=persistent_state)
        results.append(result)
        if result.status == "COMPLETED":
            for domain, value in result.domain_scores.items():
                totals[domain] += value
            for domain, count in result.domain_opportunities.items():
                opportunities[domain] += count
        if on_result is not None:
            on_result(result)

    per_domain: dict[str, float | None] = {}
    for domain in DOMAIN_BY_ID:
        count = opportunities.get(domain, 0)
        per_domain[domain] = (totals.get(domain, 0.0) / count) if count else None

    mandatory_pass = {
        d: (per_domain[d] is not None and per_domain[d] >= mandatory_threshold)
        for d in MANDATORY_DOMAINS
    }
    level_counts = Counter(s.level.value for s in scenarios)
    provenance_counts = Counter(s.provenance for s in scenarios)
    family_counts = Counter(s.family for s in scenarios)
    status_counts = Counter(r.status for r in results)

    return ExamReport(
        benchmark_version=__version__,
        contestant=agent.name,
        scenario_count=len(scenarios),
        per_domain=per_domain,
        opportunities=dict(opportunities),
        mandatory_pass=mandatory_pass,
        traces=results,
        metadata={
            "pack_sha256": pack_hash(scenarios),
            "level_counts": dict(level_counts),
            "provenance_counts": dict(provenance_counts),
            "family_counts": dict(family_counts),
            "status_counts": dict(status_counts),
            "infrastructure_error_count": int(status_counts.get("INFRASTRUCTURE_ERROR", 0)),
        },
    )


def summarize_repeated(reports: list[ExamReport]) -> dict[str, dict[str, float | None]]:
    summary: dict[str, dict[str, float | None]] = {}
    for domain in DOMAIN_BY_ID:
        values = [r.per_domain[domain] for r in reports if r.per_domain[domain] is not None]
        if not values:
            summary[domain] = {"mean": None, "stderr": None, "n": 0}
            continue
        numeric = [float(v) for v in values]
        if len(numeric) == 1:
            stderr = 0.0
        else:
            m = mean(numeric)
            variance = sum((x - m) ** 2 for x in numeric) / (len(numeric) - 1)
            stderr = sqrt(variance / len(numeric))
        summary[domain] = {"mean": mean(numeric), "stderr": stderr, "n": len(numeric)}
    return summary
