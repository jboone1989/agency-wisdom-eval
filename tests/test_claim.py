from copy import deepcopy

from awe.baselines import OracleBaseline
from awe.claim import WisdomClaimPolicy, evaluate_claim
from awe.packs import public_pack
from awe.runner import run_exam


def test_public_only_evidence_cannot_support_formal_claim():
    reports = [run_exam(OracleBaseline(), public_pack()) for _ in range(3)]
    decision = evaluate_claim(reports)
    assert not decision.eligible
    assert any("holdout" in reason for reason in decision.reasons)


def test_policy_requires_repeated_runs():
    report = run_exam(OracleBaseline(), public_pack())
    decision = evaluate_claim(
        [report],
        WisdomClaimPolicy(require_hidden_evidence=False, required_runs=3),
    )
    assert not decision.eligible
    assert any("independent runs" in reason for reason in decision.reasons)
