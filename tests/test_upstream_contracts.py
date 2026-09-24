from pathlib import Path
import json

from awe.upstream_contracts import (
    verify_apollo_insider_checkout,
    verify_machiavelli_checkout,
    verify_metr_task_standard_checkout,
    verify_osworld_checkout,
    verify_sotopia_checkout,
)


def test_upstream_contract_verifiers_detect_expected_checkout_shape(tmp_path: Path):
    m = tmp_path / "m"
    (m / "machiavelli/agent").mkdir(parents=True)
    (m / "machiavelli/game").mkdir(parents=True)
    (m / "machiavelli/agent/base_agent.py").write_text("class BaseAgent: pass")
    (m / "machiavelli/game/machiavelli_env.py").write_text(
        "choice_texts game_state Trajectory MachiavelliEnv"
    )
    (m / "generate_trajectories.py").write_text("")
    (m / "evaluate_trajectories.py").write_text("")
    assert verify_machiavelli_checkout(m).ok

    s = tmp_path / "s"
    (s / "sotopia/agents").mkdir(parents=True)
    (s / "sotopia/messages").mkdir(parents=True)
    (s / "sotopia/cli/benchmark").mkdir(parents=True)
    (s / "sotopia/agents/base_agent.py").write_text("")
    (s / "sotopia/agents/llm_agent.py").write_text("")
    (s / "sotopia/messages/message_classes.py").write_text(
        "class Observation available_actions class AgentAction action_type"
    )
    (s / "sotopia/cli/benchmark/benchmark.py").write_text(
        "def _benchmark_impl(): pass\nagent_class"
    )
    assert verify_sotopia_checkout(s).ok

    o = tmp_path / "o"
    (o / "mm_agents").mkdir(parents=True)
    (o / "desktop_env").mkdir(parents=True)
    (o / "scripts/python").mkdir(parents=True)
    (o / "mm_agents/agent.py").write_text("def predict(): pass\na11y_tree pyautogui")
    (o / "desktop_env/actions.py").write_text('"WAIT" "FAIL" "DONE"')
    (o / "desktop_env/desktop_env.py").write_text("")
    (o / "scripts/python/run_multienv_glm.py").write_text("")
    assert verify_osworld_checkout(o).ok

    mt = tmp_path / "mt"
    (mt / "examples/gaia").mkdir(parents=True)
    (mt / "examples/agentbench").mkdir(parents=True)
    (mt / "examples/gaia/gaia.py").write_text(
        "standard_version HF_TOKEN gaia-benchmark/GAIA def score"
    )
    (mt / "examples/agentbench/agentbench.py").write_text(
        "standard_version THUDM/AgentBench def score"
    )
    assert verify_metr_task_standard_checkout(mt).ok

    a = tmp_path / "a"
    (a / "prompts").mkdir(parents=True)
    (a / "README.md").write_text("")
    (a / "prompts/default.json").write_text(json.dumps({
        "messages": [{"role": "system", "content": "x"}],
        "misalignment_string": "buy",
        "deception_trigger": "success",
        "doubling_down_trigger": "did you know",
        "canary": "do not train",
    }))
    assert verify_apollo_insider_checkout(a).ok
