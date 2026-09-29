from __future__ import annotations

from copy import deepcopy

from awe.hillclimb import compare_hillclimb, optimizer_view
from awe.packs import generated_holdout, generated_train
from awe.models import ExamReport, ScenarioResult


def _report(score: float, *, pack: str, infra: int = 0, scenario: str = "case") -> ExamReport:
    trace = ScenarioResult(
        scenario_id=scenario,
        family="test",
        level="E1",
        provenance="generated",
        generation_seed_hash=None,
        status="INFRASTRUCTURE_ERROR" if infra else "COMPLETED",
        completed=not bool(infra),
        invalid_action=False,
        steps=[],
        domain_scores={} if infra else {"goal_pursuit": score},
        domain_opportunities={} if infra else {"goal_pursuit": 1},
        error_type="TimeoutError" if infra else None,
        error_detail="timeout" if infra else None,
    )
    return ExamReport(
        benchmark_version="test",
        contestant="candidate",
        scenario_count=1,
        per_domain={"goal_pursuit": None if infra else score},
        opportunities={} if infra else {"goal_pursuit": 1},
        mandatory_pass={},
        traces=[trace],
        metadata={"pack_sha256": pack, "infrastructure_error_count": infra},
    )


def test_promotes_only_when_train_and_hidden_clear_noise():
    decision = compare_hillclimb(
        train_baseline=[_report(0.40, pack="train"), _report(0.42, pack="train")],
        train_candidate=[_report(0.70, pack="train"), _report(0.72, pack="train")],
        hidden_baseline=[_report(0.45, pack="hidden"), _report(0.46, pack="hidden")],
        hidden_candidate=[_report(0.68, pack="hidden"), _report(0.70, pack="hidden")],
        regression_baseline=[_report(0.90, pack="reg"), _report(0.90, pack="reg")],
        regression_candidate=[_report(0.90, pack="reg"), _report(0.89, pack="reg")],
    )
    assert decision.decision == "PROMOTE"
    assert decision.train_gain > 0
    assert decision.hidden_gain > 0


def test_train_gain_without_hidden_transfer_rolls_back():
    decision = compare_hillclimb(
        train_baseline=[_report(0.40, pack="train"), _report(0.40, pack="train")],
        train_candidate=[_report(0.90, pack="train"), _report(0.90, pack="train")],
        hidden_baseline=[_report(0.60, pack="hidden"), _report(0.60, pack="hidden")],
        hidden_candidate=[_report(0.60, pack="hidden"), _report(0.60, pack="hidden")],
    )
    assert decision.decision == "ROLLBACK_NO_GENERALIZATION"


def test_infrastructure_error_is_not_counted_as_capability_failure():
    decision = compare_hillclimb(
        train_baseline=[_report(0.40, pack="train"), _report(0.40, pack="train")],
        train_candidate=[_report(0.90, pack="train"), _report(0.90, pack="train")],
        hidden_baseline=[_report(0.60, pack="hidden"), _report(0.60, pack="hidden")],
        hidden_candidate=[_report(0.0, pack="hidden", infra=1), _report(0.90, pack="hidden")],
    )
    assert decision.decision == "INVALID_INFRASTRUCTURE"


def test_optimizer_view_never_exposes_hidden_traces_or_case_ids():
    decision = compare_hillclimb(
        train_baseline=[_report(0.20, pack="train"), _report(0.20, pack="train")],
        train_candidate=[_report(0.80, pack="train", scenario="train.case.1"), _report(0.80, pack="train", scenario="train.case.1")],
        hidden_baseline=[_report(0.20, pack="secret-hidden", scenario="secret.hidden.1"), _report(0.20, pack="secret-hidden", scenario="secret.hidden.1")],
        hidden_candidate=[_report(0.80, pack="secret-hidden", scenario="secret.hidden.1"), _report(0.80, pack="secret-hidden", scenario="secret.hidden.1")],
    )
    view = optimizer_view(decision, latest_train_candidate=_report(0.50, pack="train", scenario="train.visible"))
    encoded = repr(view)
    assert "secret.hidden.1" not in encoded
    assert "train.visible" in encoded
    assert "traces" not in view["hidden"]


def test_pack_mismatch_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="pack mismatch"):
        compare_hillclimb(
            train_baseline=[_report(0.2, pack="train-a"), _report(0.2, pack="train-a")],
            train_candidate=[_report(0.8, pack="train-b"), _report(0.8, pack="train-b")],
            hidden_baseline=[_report(0.2, pack="hidden"), _report(0.2, pack="hidden")],
            hidden_candidate=[_report(0.8, pack="hidden"), _report(0.8, pack="hidden")],
        )


def test_incomplete_regression_pair_is_rejected():
    import pytest

    with pytest.raises(ValueError, match="regression baseline and candidate"):
        compare_hillclimb(
            train_baseline=[_report(0.2, pack="train"), _report(0.2, pack="train")],
            train_candidate=[_report(0.8, pack="train"), _report(0.8, pack="train")],
            hidden_baseline=[_report(0.2, pack="hidden"), _report(0.2, pack="hidden")],
            hidden_candidate=[_report(0.8, pack="hidden"), _report(0.8, pack="hidden")],
            regression_baseline=[_report(0.9, pack="reg"), _report(0.9, pack="reg")],
        )


def test_generated_train_matches_distribution_but_is_explicitly_train_visible():
    train = generated_train("visible-seed", 4)
    hidden_shape = generated_holdout("visible-seed", 4)

    assert [row.id for row in train] == [row.id for row in hidden_shape]
    assert all(row.provenance == "generated-train" for row in train)
    assert all(row.provenance == "generated-holdout" for row in hidden_shape)


def test_optimizer_view_clusters_train_failures_only():
    decision = compare_hillclimb(
        train_baseline=[_report(0.2, pack="train"), _report(0.2, pack="train")],
        train_candidate=[_report(0.8, pack="train"), _report(0.8, pack="train")],
        hidden_baseline=[_report(0.2, pack="hidden"), _report(0.2, pack="hidden")],
        hidden_candidate=[_report(0.8, pack="hidden"), _report(0.8, pack="hidden")],
    )
    view = optimizer_view(
        decision,
        latest_train_candidate=_report(0.5, pack="train", scenario="train.failure"),
    )

    assert view["train"]["failure_clusters"][0]["count"] == 1
    assert view["train"]["failure_clusters"][0]["scenario_ids"] == ["train.failure"]
    assert "failure_clusters" not in view["hidden"]
