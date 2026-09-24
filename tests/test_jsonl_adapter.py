import sys

from awe.adapters.jsonl import JsonLineSubprocessAgent
from awe.packs import public_pack
from awe.runner import run_scenario


def test_jsonl_subprocess_contestant_protocol():
    scenario = public_pack()[0]
    with JsonLineSubprocessAgent(
        [sys.executable, "tests/contestant_stub.py"],
        name="stub",
        timeout_seconds=2,
    ) as agent:
        result = run_scenario(agent, scenario)
    assert result.completed
    assert not result.invalid_action
    assert list(result.domain_scores.values()) == [1.0]
