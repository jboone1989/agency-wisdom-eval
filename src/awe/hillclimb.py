from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt
from statistics import mean, stdev
from typing import Iterable, Sequence

from .models import ExamReport, ScenarioResult


@dataclass(frozen=True)
class RepeatedScore:
    mean: float | None
    stderr: float | None
    n: int
    infrastructure_error_count: int
    pack_sha256: str | None


@dataclass(frozen=True)
class HillclimbDecision:
    decision: str
    reason: str
    train_baseline: RepeatedScore
    train_candidate: RepeatedScore
    hidden_baseline: RepeatedScore
    hidden_candidate: RepeatedScore
    regression_baseline: RepeatedScore | None
    regression_candidate: RepeatedScore | None
    train_gain: float | None
    hidden_gain: float | None
    regression_gain: float | None
    train_noise_floor: float | None
    hidden_noise_floor: float | None
    max_regression: float
    min_repeats: int

    def to_dict(self) -> dict:
        return asdict(self)


def _report_score(report: ExamReport, domains: set[str] | None = None) -> float | None:
    values = [
        float(value)
        for domain, value in report.per_domain.items()
        if value is not None and (domains is None or domain in domains)
    ]
    return mean(values) if values else None


def _infra_count(report: ExamReport) -> int:
    return int(
        (report.metadata or {}).get("infrastructure_error_count")
        or sum(1 for row in report.traces if row.status == "INFRASTRUCTURE_ERROR")
    )


def _pack_hash(report: ExamReport) -> str | None:
    value = (report.metadata or {}).get("pack_sha256")
    return str(value) if value else None


def _repeated(
    reports: Sequence[ExamReport],
    *,
    domains: set[str] | None = None,
) -> RepeatedScore:
    scores = [
        score
        for score in (_report_score(report, domains) for report in reports)
        if score is not None
    ]
    stderr = None
    if len(scores) >= 2:
        stderr = stdev(scores) / sqrt(len(scores))
    return RepeatedScore(
        mean=mean(scores) if scores else None,
        stderr=stderr,
        n=len(scores),
        infrastructure_error_count=sum(_infra_count(report) for report in reports),
        pack_sha256=_single_pack_hash(reports),
    )


def _single_pack_hash(reports: Sequence[ExamReport]) -> str | None:
    values = {_pack_hash(report) for report in reports if _pack_hash(report)}
    if len(values) > 1:
        raise ValueError("repeated reports must use one exact evaluator pack")
    return next(iter(values), None)


def _assert_same_pack(
    baseline: Sequence[ExamReport],
    candidate: Sequence[ExamReport],
    *,
    split: str,
) -> None:
    left = _single_pack_hash(baseline)
    right = _single_pack_hash(candidate)
    if left is not None and right is not None and left != right:
        raise ValueError(f"{split} baseline/candidate pack mismatch")


def _gain(candidate: RepeatedScore, baseline: RepeatedScore) -> float | None:
    if candidate.mean is None or baseline.mean is None:
        return None
    return candidate.mean - baseline.mean


def _noise_floor(
    candidate: RepeatedScore,
    baseline: RepeatedScore,
    *,
    minimum_effect: float,
) -> float | None:
    if candidate.stderr is None or baseline.stderr is None:
        return None
    paired_stderr = sqrt(candidate.stderr ** 2 + baseline.stderr ** 2)
    return max(float(minimum_effect), 2.0 * paired_stderr)


def compare_hillclimb(
    *,
    train_baseline: Sequence[ExamReport],
    train_candidate: Sequence[ExamReport],
    hidden_baseline: Sequence[ExamReport],
    hidden_candidate: Sequence[ExamReport],
    regression_baseline: Sequence[ExamReport] = (),
    regression_candidate: Sequence[ExamReport] = (),
    domains: Iterable[str] | None = None,
    minimum_effect: float = 0.01,
    max_regression: float = 0.01,
    min_repeats: int = 2,
) -> HillclimbDecision:
    """Decide whether one bounded mutation generalizes.

    Train failures may be shown to the mutation agent. Hidden traces must remain
    evaluator-private; only aggregate statistics from this decision should cross
    that boundary.
    """
    domain_set = {str(value) for value in domains} if domains is not None else None
    if bool(regression_baseline) != bool(regression_candidate):
        raise ValueError("regression baseline and candidate must be supplied together")
    _assert_same_pack(train_baseline, train_candidate, split="train")
    _assert_same_pack(hidden_baseline, hidden_candidate, split="hidden")
    if regression_baseline or regression_candidate:
        _assert_same_pack(regression_baseline, regression_candidate, split="regression")

    tb = _repeated(train_baseline, domains=domain_set)
    tc = _repeated(train_candidate, domains=domain_set)
    hb = _repeated(hidden_baseline, domains=domain_set)
    hc = _repeated(hidden_candidate, domains=domain_set)
    rb = _repeated(regression_baseline, domains=domain_set) if regression_baseline else None
    rc = _repeated(regression_candidate, domains=domain_set) if regression_candidate else None

    train_gain = _gain(tc, tb)
    hidden_gain = _gain(hc, hb)
    regression_gain = _gain(rc, rb) if rb is not None and rc is not None else None
    train_noise = _noise_floor(tc, tb, minimum_effect=minimum_effect)
    hidden_noise = _noise_floor(hc, hb, minimum_effect=minimum_effect)

    all_scores = [tb, tc, hb, hc] + ([rb, rc] if rb is not None and rc is not None else [])
    if any(row.infrastructure_error_count > 0 for row in all_scores if row is not None):
        decision = "INVALID_INFRASTRUCTURE"
        reason = "one or more trials had infrastructure errors; capability evidence is invalid"
    elif any(
        row.n < min_repeats
        for row in (
            tb,
            tc,
            hb,
            hc,
            *(
                (rb, rc)
                if rb is not None and rc is not None
                else ()
            ),
        )
    ):
        decision = "WAIT_FOR_REPEATS"
        reason = "not enough repeated runs to measure evaluator variance"
    elif train_gain is None or hidden_gain is None or train_noise is None or hidden_noise is None:
        decision = "WAIT_FOR_EVIDENCE"
        reason = "a required split has no scored evidence"
    elif train_gain < train_noise:
        decision = "ROLLBACK_NO_TRAIN_GAIN"
        reason = "candidate improvement does not clear the train noise floor"
    elif hidden_gain < hidden_noise:
        decision = "ROLLBACK_NO_GENERALIZATION"
        reason = "candidate improvement does not clear the hidden noise floor"
    elif regression_gain is not None and regression_gain < -abs(float(max_regression)):
        decision = "ROLLBACK_REGRESSION"
        reason = "candidate regressed protected regression behavior beyond the allowed bound"
    else:
        decision = "PROMOTE"
        reason = "candidate improved train and hidden splits beyond measured noise without protected regression"

    return HillclimbDecision(
        decision=decision,
        reason=reason,
        train_baseline=tb,
        train_candidate=tc,
        hidden_baseline=hb,
        hidden_candidate=hc,
        regression_baseline=rb,
        regression_candidate=rc,
        train_gain=train_gain,
        hidden_gain=hidden_gain,
        regression_gain=regression_gain,
        train_noise_floor=train_noise,
        hidden_noise_floor=hidden_noise,
        max_regression=float(max_regression),
        min_repeats=int(min_repeats),
    )


def _train_failures(report: ExamReport) -> list[dict]:
    rows: list[dict] = []
    for result in report.traces:
        if result.status == "INFRASTRUCTURE_ERROR":
            continue
        score_values = list(result.domain_scores.values())
        score = mean(score_values) if score_values else None
        if result.status == "COMPLETED" and score is not None and score >= 1.0:
            continue
        rows.append({
            "scenario_id": result.scenario_id,
            "status": result.status,
            "domain_scores": dict(result.domain_scores),
            "selected_actions": [step.selected_action for step in result.steps],
            "error_type": result.error_type,
        })
    return rows


def _failure_clusters(failures: Sequence[dict]) -> list[dict]:
    clusters: dict[tuple[str, str, str], list[str]] = {}
    for row in failures:
        scores = row.get("domain_scores") or {}
        weakest = (
            min(scores, key=lambda key: float(scores[key]))
            if scores else "unscored"
        )
        key = (
            str(row.get("status") or "UNKNOWN"),
            str(row.get("error_type") or "NONE"),
            str(weakest),
        )
        clusters.setdefault(key, []).append(str(row.get("scenario_id") or ""))
    ranked = sorted(
        clusters.items(),
        key=lambda item: (-len(item[1]), item[0]),
    )
    return [
        {
            "status": key[0],
            "error_type": key[1],
            "weakest_domain": key[2],
            "count": len(ids),
            "scenario_ids": ids,
        }
        for key, ids in ranked
    ]


def optimizer_view(
    decision: HillclimbDecision,
    *,
    latest_train_candidate: ExamReport | None = None,
) -> dict:
    """Return the only view a mutation agent should receive.

    Hidden scenario ids, traces, actions, prompts, and failure reasons are
    intentionally absent. The optimizer gets aggregate hidden evidence only.
    """
    failures = (
        _train_failures(latest_train_candidate)
        if latest_train_candidate is not None
        else []
    )
    payload = {
        "decision": decision.decision,
        "reason": decision.reason,
        "train": {
            "baseline": asdict(decision.train_baseline),
            "candidate": asdict(decision.train_candidate),
            "gain": decision.train_gain,
            "noise_floor": decision.train_noise_floor,
            "failures": failures,
            "failure_clusters": _failure_clusters(failures),
        },
        "hidden": {
            "baseline_mean": decision.hidden_baseline.mean,
            "candidate_mean": decision.hidden_candidate.mean,
            "gain": decision.hidden_gain,
            "noise_floor": decision.hidden_noise_floor,
            "n_baseline": decision.hidden_baseline.n,
            "n_candidate": decision.hidden_candidate.n,
            "infrastructure_error_count": (
                decision.hidden_baseline.infrastructure_error_count
                + decision.hidden_candidate.infrastructure_error_count
            ),
        },
        "regression": None,
    }
    if decision.regression_baseline is not None and decision.regression_candidate is not None:
        payload["regression"] = {
            "baseline_mean": decision.regression_baseline.mean,
            "candidate_mean": decision.regression_candidate.mean,
            "gain": decision.regression_gain,
            "max_regression": decision.max_regression,
        }
    return payload


__all__ = [
    "RepeatedScore",
    "HillclimbDecision",
    "compare_hillclimb",
    "optimizer_view",
]
