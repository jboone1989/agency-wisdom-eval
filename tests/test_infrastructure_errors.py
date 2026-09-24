import sys

from awe.adapters.jsonl import JsonLineSubprocessAgent
from awe.packs import public_pack
from awe.runner import run_scenario


def test_jsonl_contestant_error_becomes_infrastructure_error():
    with JsonLineSubprocessAgent(
        [sys.executable, "tests/contestant_error_stub.py"],
        name="error-stub",
        timeout_seconds=2,
    ) as agent:
        result = run_scenario(agent, public_pack()[0])
    assert result.status == "INFRASTRUCTURE_ERROR"
    assert result.error_type == "ContestantExecutionError"
    assert "LLMProviderError" in (result.error_detail or "")
    assert result.domain_scores == {}
    assert result.domain_opportunities == {}
