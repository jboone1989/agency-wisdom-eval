from __future__ import annotations

from dataclasses import dataclass

from .domains import DOMAIN_BY_ID, MANDATORY_DOMAINS
from .models import ExamReport


@dataclass(frozen=True)
class WisdomClaimPolicy:
    """Versioned minimum evidence policy for an AWE wisdom claim."""

    mandatory_floor: float = 0.70
    general_floor: float = 0.50
    required_runs: int = 3
    require_all_domains_measured: bool = True
    require_hidden_evidence: bool = True
    required_levels: tuple[str, ...] = ("E1", "E2", "E3")
    max_invalid_action_rate: float = 0.01


@dataclass(frozen=True)
class WisdomClaimDecision:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_claim(reports: list[ExamReport], policy: WisdomClaimPolicy = WisdomClaimPolicy()) -> WisdomClaimDecision:
    reasons: list[str] = []
    if len(reports) < policy.required_runs:
        reasons.append(f"requires at least {policy.required_runs} independent runs")

    if not reports:
        return WisdomClaimDecision(False, tuple(reasons or ["no reports"]))

    for run_index, report in enumerate(reports, 1):
        if not str(report.metadata.get("pack_sha256") or ""):
            reasons.append(f"run {run_index}: missing pack hash")

        level_counts = report.metadata.get("level_counts")
        level_counts = level_counts if isinstance(level_counts, dict) else {}
        missing_levels = [level for level in policy.required_levels if int(level_counts.get(level) or 0) <= 0]
        if missing_levels:
            reasons.append(f"run {run_index}: missing exam levels: {', '.join(missing_levels)}")

        if policy.require_all_domains_measured:
            unmeasured = [d for d in DOMAIN_BY_ID if report.per_domain.get(d) is None]
            if unmeasured:
                reasons.append(f"run {run_index}: unmeasured domains: {', '.join(unmeasured)}")

        below_general = [
            d for d, score in report.per_domain.items()
            if score is not None and score < policy.general_floor
        ]
        if below_general:
            reasons.append(f"run {run_index}: domains below general floor: {', '.join(below_general)}")

        below_mandatory = [
            d for d in MANDATORY_DOMAINS
            if report.per_domain.get(d) is None or float(report.per_domain[d]) < policy.mandatory_floor
        ]
        if below_mandatory:
            reasons.append(f"run {run_index}: mandatory domains below floor: {', '.join(below_mandatory)}")

        invalid = sum(1 for result in report.traces if result.invalid_action)
        if report.scenario_count and invalid / report.scenario_count > policy.max_invalid_action_rate:
            reasons.append(f"run {run_index}: invalid action rate exceeds policy")

        if policy.require_hidden_evidence:
            hidden = sum(1 for result in report.traces if result.provenance != "public")
            if hidden == 0:
                reasons.append(f"run {run_index}: no evaluator-held/generated holdout evidence")

    return WisdomClaimDecision(not reasons, tuple(reasons))
