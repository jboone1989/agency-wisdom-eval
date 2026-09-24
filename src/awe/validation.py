from __future__ import annotations

from collections import Counter

from .domains import DOMAIN_BY_ID, MANDATORY_DOMAINS
from .models import Scenario


class ValidationError(ValueError):
    pass


def validate_scenario(scenario: Scenario) -> None:
    if scenario.start_node not in scenario.nodes:
        raise ValidationError(f"{scenario.id}: missing start node")
    unknown_domains = [d for d in scenario.domains if d not in DOMAIN_BY_ID]
    if unknown_domains:
        raise ValidationError(f"{scenario.id}: unknown domains {unknown_domains}")
    for node in scenario.nodes.values():
        action_ids = [a.id for a in node.actions]
        if len(action_ids) != len(set(action_ids)):
            raise ValidationError(f"{scenario.id}/{node.id}: duplicate action id")
        if not node.terminal and not node.actions:
            raise ValidationError(f"{scenario.id}/{node.id}: non-terminal node has no actions")
        if set(node.transitions) != set(action_ids):
            raise ValidationError(f"{scenario.id}/{node.id}: transitions must match actions")
        for transition in node.transitions.values():
            if transition.next_node is not None and transition.next_node not in scenario.nodes:
                raise ValidationError(f"{scenario.id}/{node.id}: transition points to unknown node")
            for delta in transition.score:
                if delta.domain not in DOMAIN_BY_ID:
                    raise ValidationError(f"{scenario.id}/{node.id}: score uses unknown domain")
                if not 0.0 <= delta.value <= 1.0:
                    raise ValidationError(f"{scenario.id}/{node.id}: score outside [0,1]")


def coverage_report(scenarios: list[Scenario]) -> dict[str, int]:
    counts = Counter()
    for scenario in scenarios:
        for domain in scenario.domains:
            counts[domain] += 1
    return {domain: counts[domain] for domain in DOMAIN_BY_ID}


def assert_comprehensive_coverage(scenarios: list[Scenario]) -> None:
    coverage = coverage_report(scenarios)
    missing = [d for d, n in coverage.items() if n == 0]
    if missing:
        raise ValidationError(f"uncovered domains: {missing}")
    missing_mandatory = [d for d in MANDATORY_DOMAINS if coverage[d] < 1]
    if missing_mandatory:
        raise ValidationError(f"mandatory domains uncovered: {missing_mandatory}")
