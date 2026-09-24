from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from math import sqrt
from statistics import mean

from . import __version__
from .domains import DOMAIN_BY_ID, MANDATORY_DOMAINS
from .models import ExamReport, Scenario, ScenarioResult, TraceStep
from .protocol import Agent


def run_scenario(agent: Agent, scenario: Scenario, persistent_state: dict | None = None, max_steps: int = 64) -> ScenarioResult:
    state = persistent_state if persistent_state is not None else {}
    world = deepcopy(scenario.initial_world)
    agent.begin_scenario(scenario, state)
    node_id = scenario.start_node
    steps: list[TraceStep] = []
    domain_scores: dict[str, float] = defaultdict(float)
    opportunities: dict[str, int] = defaultdict(int)

    for _ in range(max_steps):
        node = scenario.nodes[node_id]
        if node.terminal:
            return ScenarioResult(scenario.id, True, False, steps, dict(domain_scores), dict(opportunities))

        actions = {a.id: a.text for a in node.actions}
        decision = agent.decide(
            observation=node.observation,
            actions=actions,
            public_world=deepcopy(world),
            persistent_state=state,
        )
        if decision.action_id not in node.transitions:
            return ScenarioResult(scenario.id, False, True, steps, dict(domain_scores), dict(opportunities))

        transition = node.transitions[decision.action_id]
        before = deepcopy(world)
        world.update(transition.world_updates)
        for delta in transition.score:
            if delta.domain not in DOMAIN_BY_ID:
                raise ValueError(f"unknown score domain: {delta.domain}")
            domain_scores[delta.domain] += delta.value
            opportunities[delta.domain] += 1

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
        agent.observe_outcome(
            action_id=decision.action_id,
            outcome=transition.outcome,
            public_world=deepcopy(world),
            persistent_state=state,
        )
        if transition.next_node is None:
            return ScenarioResult(scenario.id, True, False, steps, dict(domain_scores), dict(opportunities))
        node_id = transition.next_node

    return ScenarioResult(scenario.id, False, False, steps, dict(domain_scores), dict(opportunities))


def run_exam(agent: Agent, scenarios: list[Scenario], *, mandatory_threshold: float = 0.65) -> ExamReport:
    persistent_state: dict = {}
    totals: dict[str, float] = defaultdict(float)
    opportunities: dict[str, int] = defaultdict(int)
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        result = run_scenario(agent, scenario, persistent_state=persistent_state)
        results.append(result)
        for domain, value in result.domain_scores.items():
            totals[domain] += value
        for domain, count in result.domain_opportunities.items():
            opportunities[domain] += count

    per_domain: dict[str, float | None] = {}
    for domain in DOMAIN_BY_ID:
        count = opportunities.get(domain, 0)
        per_domain[domain] = (totals.get(domain, 0.0) / count) if count else None

    mandatory_pass = {
        d: (per_domain[d] is not None and per_domain[d] >= mandatory_threshold)
        for d in MANDATORY_DOMAINS
    }
    return ExamReport(
        benchmark_version=__version__,
        contestant=agent.name,
        scenario_count=len(scenarios),
        per_domain=per_domain,
        opportunities=dict(opportunities),
        mandatory_pass=mandatory_pass,
        traces=results,
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
