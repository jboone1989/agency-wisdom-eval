from __future__ import annotations

from typing import Any, Mapping, Sequence
from uuid import uuid4

from .external_jsonl import ExternalContestantClient


def osworld_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "pyautogui",
            "description": (
                "Return one valid pyautogui Python action for the OSWorld guest. "
                "The OSWorld environment, not Ferro, executes the code."
            ),
            "input_schema": {
                "type": "object",
                "properties": {"code": {"type": "string"}},
                "required": ["code"],
                "additionalProperties": False,
            },
        },
        {
            "name": "WAIT",
            "description": "Ask OSWorld to wait without interacting.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "DONE",
            "description": "Declare the OSWorld task complete.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
        {
            "name": "FAIL",
            "description": "Declare that the OSWorld task cannot be completed.",
            "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    ]


class FerroOSWorldAgent:
    """OSWorld 2.x-compatible text/a11y agent backed by Ferro.

    The official OSWorld environment executes returned pyautogui actions and owns
    task setup/evaluation. This adapter intentionally consumes accessibility-tree
    observations only; screenshot-only runs require a genuinely multimodal Ferro
    provider and are not silently downgraded to text.
    """

    def __init__(
        self,
        contestant_command: Sequence[str],
        *,
        observation_type: str = "a11y_tree",
        timeout_seconds: float = 90.0,
    ) -> None:
        if observation_type not in {"a11y_tree", "screenshot_a11y_tree"}:
            raise ValueError(
                "FerroOSWorldAgent currently requires an accessibility-tree observation"
            )
        self.observation_type = observation_type
        self.client = ExternalContestantClient(
            contestant_command,
            timeout_seconds=timeout_seconds,
        )
        self._episode_id = ""
        self._last_action = ""
        self._turn = 0

    def reset(self, _logger=None) -> None:
        self._episode_id = ""
        self._last_action = ""
        self._turn = 0

    def _observation_text(self, obs: Mapping[str, Any]) -> str:
        tree = obs.get("accessibility_tree")
        if tree is None:
            raise ValueError(
                "OSWorld observation has no accessibility_tree; "
                "refusing to pretend a text-only Ferro bridge saw the screenshot"
            )
        return str(tree)

    def predict(self, instruction: str, obs: Mapping[str, Any]):
        observation = self._observation_text(obs)
        if not self._episode_id:
            self._episode_id = uuid4().hex
            self.client.begin_episode(
                benchmark_id="osworld",
                episode_id=self._episode_id,
                title=str(instruction)[:200],
                metadata={
                    "observation_type": self.observation_type,
                    "action_space": "pyautogui",
                },
            )
        elif self._last_action:
            self.client.outcome(
                action=self._last_action,
                outcome=observation,
                public_state={"turn": self._turn},
            )

        decision = self.client.tool_turn(
            observation=observation,
            instruction=str(instruction),
            tools=osworld_tools(),
            context={
                "turn": self._turn,
                "observation_type": self.observation_type,
                "action_space": "pyautogui",
            },
        )
        self._turn += 1

        if decision.get("kind") == "final":
            response = str(decision.get("response") or "")
            self._last_action = "DONE"
            return response, ["DONE"]

        tool_name = str(decision.get("tool_name") or "")
        arguments = decision.get("arguments")
        arguments = arguments if isinstance(arguments, Mapping) else {}
        if tool_name == "pyautogui":
            code = str(arguments.get("code") or "").strip()
            if not code:
                raise ValueError("OSWorld pyautogui action requires code")
            if "pyautogui" not in code:
                raise ValueError("OSWorld pyautogui code must explicitly call pyautogui")
            action = code
        elif tool_name in {"WAIT", "DONE", "FAIL"}:
            action = tool_name
        else:
            raise ValueError(f"unsupported OSWorld action {tool_name!r}")
        self._last_action = action
        return {"source": "Ferro/AWE", "action": action}, [action]

    def close(self) -> None:
        self.client.close()
