from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ContractCheck:
    benchmark_id: str
    checkout: str
    ok: bool
    reasons: tuple[str, ...]


def _missing(root: Path, relative_paths: tuple[str, ...]) -> list[str]:
    return [
        f"missing {relative}"
        for relative in relative_paths
        if not (root / relative).is_file()
    ]


def verify_machiavelli_checkout(path: str | Path) -> ContractCheck:
    root = Path(path)
    reasons = _missing(root, (
        "machiavelli/agent/base_agent.py",
        "machiavelli/game/machiavelli_env.py",
        "generate_trajectories.py",
        "evaluate_trajectories.py",
    ))
    env = root / "machiavelli/game/machiavelli_env.py"
    if env.is_file():
        text = env.read_text(encoding="utf-8")
        for token in ("choice_texts", "game_state", "Trajectory", "MachiavelliEnv"):
            if token not in text:
                reasons.append(f"upstream contract token missing: {token}")
    return ContractCheck("machiavelli", str(root), not reasons, tuple(reasons))


def verify_sotopia_checkout(path: str | Path) -> ContractCheck:
    root = Path(path)
    reasons = _missing(root, (
        "sotopia/agents/base_agent.py",
        "sotopia/agents/llm_agent.py",
        "sotopia/messages/message_classes.py",
        "sotopia/cli/benchmark/benchmark.py",
    ))
    messages = root / "sotopia/messages/message_classes.py"
    if messages.is_file():
        text = messages.read_text(encoding="utf-8")
        for token in ("class Observation", "available_actions", "class AgentAction", "action_type"):
            if token not in text:
                reasons.append(f"upstream contract token missing: {token}")
    benchmark = root / "sotopia/cli/benchmark/benchmark.py"
    if benchmark.is_file():
        text = benchmark.read_text(encoding="utf-8")
        for token in ("def _benchmark_impl", "agent_class"):
            if token not in text:
                reasons.append(f"benchmark hook missing: {token}")
    return ContractCheck("sotopia", str(root), not reasons, tuple(reasons))


def verify_osworld_checkout(path: str | Path) -> ContractCheck:
    root = Path(path)
    reasons = _missing(root, (
        "mm_agents/agent.py",
        "desktop_env/actions.py",
        "desktop_env/desktop_env.py",
        "scripts/python/run_multienv_glm.py",
    ))
    agent = root / "mm_agents/agent.py"
    if agent.is_file():
        text = agent.read_text(encoding="utf-8")
        for token in ("def predict", "a11y_tree", "pyautogui"):
            if token not in text:
                reasons.append(f"OSWorld agent contract token missing: {token}")
    actions = root / "desktop_env/actions.py"
    if actions.is_file():
        text = actions.read_text(encoding="utf-8")
        for token in ('"WAIT"', '"FAIL"', '"DONE"'):
            if token not in text:
                reasons.append(f"OSWorld terminal action missing: {token}")
    return ContractCheck("osworld", str(root), not reasons, tuple(reasons))


def verify_metr_task_standard_checkout(path: str | Path) -> ContractCheck:
    root = Path(path)
    reasons = _missing(root, (
        "examples/gaia/gaia.py",
        "examples/agentbench/agentbench.py",
    ))
    gaia = root / "examples/gaia/gaia.py"
    if gaia.is_file():
        text = gaia.read_text(encoding="utf-8")
        for token in ("standard_version", "HF_TOKEN", "gaia-benchmark/GAIA", "def score"):
            if token not in text:
                reasons.append(f"GAIA adaptor contract token missing: {token}")
    agentbench = root / "examples/agentbench/agentbench.py"
    if agentbench.is_file():
        text = agentbench.read_text(encoding="utf-8")
        for token in ("standard_version", "THUDM/AgentBench", "def score"):
            if token not in text:
                reasons.append(f"AgentBench adaptor contract token missing: {token}")
    return ContractCheck("metr-task-standard", str(root), not reasons, tuple(reasons))


def verify_apollo_insider_checkout(path: str | Path) -> ContractCheck:
    root = Path(path)
    reasons = _missing(root, ("README.md", "prompts/default.json"))
    prompt = root / "prompts/default.json"
    if prompt.is_file():
        try:
            payload = json.loads(prompt.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            reasons.append(f"invalid prompt json: {exc}")
        else:
            for key in (
                "messages",
                "misalignment_string",
                "deception_trigger",
                "doubling_down_trigger",
                "canary",
            ):
                if not payload.get(key):
                    reasons.append(f"Apollo public prompt missing {key}")
    return ContractCheck(
        "apollo-scheming",
        str(root),
        not reasons,
        tuple(reasons),
    )
