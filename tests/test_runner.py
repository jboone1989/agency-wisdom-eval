from awe.baselines import MyopicBaseline, OracleBaseline
from awe.packs import public_pack
from awe.runner import run_exam


def test_oracle_reference_exercises_all_public_domains():
    report = run_exam(OracleBaseline(), public_pack())
    assert report.scenario_count >= 40
    assert all(score == 1.0 for score in report.per_domain.values() if score is not None)
    assert all(report.mandatory_pass.values())


def test_myopic_reference_is_not_mistaken_for_wisdom():
    report = run_exam(MyopicBaseline(), public_pack())
    assert any(score is not None and score < 1.0 for score in report.per_domain.values())
    assert not all(report.mandatory_pass.values())


class _InfrastructureFailure:
    name = "infra-failure"

    def begin_scenario(self, scenario, persistent_state):
        pass

    def decide(self, **kwargs):
        raise RuntimeError("provider unavailable")

    def observe_outcome(self, **kwargs):
        raise AssertionError("outcome should not be called")


def test_infrastructure_error_is_not_scored_as_agent_failure():
    scenario = public_pack()[0]
    report = run_exam(_InfrastructureFailure(), [scenario])
    result = report.traces[0]
    assert result.status == "INFRASTRUCTURE_ERROR"
    assert not result.invalid_action
    assert result.error_type == "RuntimeError"
    assert report.per_domain[scenario.domains[0]] is None
    assert report.metadata["infrastructure_error_count"] == 1
