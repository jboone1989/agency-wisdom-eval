from __future__ import annotations

from typing import Any, Mapping, Sequence
from uuid import uuid4

from .external_jsonl import ExternalContestantClient


def action_tools(available_actions: Sequence[str]) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    for action_type in available_actions:
        action_type = str(action_type)
        properties: dict[str, Any] = {}
        required: list[str] = []
        if action_type in {"speak", "non-verbal communication", "action"}:
            properties["argument"] = {"type": "string"}
            required.append("argument")
        tools.append({
            "name": action_type,
            "description": f"Take the SOTOPIA action type {action_type!r}.",
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        })
    return tools


def build_sotopia_agent_class(
    contestant_command: Sequence[str],
    *,
    timeout_seconds: float = 90.0,
):
    """Return an upstream-compatible SOTOPIA BaseAgent subclass backed by Ferro."""
    try:
        from sotopia.agents import BaseAgent
        from sotopia.messages import AgentAction, Observation
    except ImportError as exc:
        raise RuntimeError("SOTOPIA upstream package is not installed") from exc

    command = tuple(str(x) for x in contestant_command)

    class FerroSotopiaAgent(BaseAgent[Observation, AgentAction]):  # type: ignore[name-defined]
        def __init__(
            self,
            agent_name: str | None = None,
            uuid_str: str | None = None,
            agent_profile: Any | None = None,
            model_name: str = "ferro-awe",
            **_kwargs: Any,
        ) -> None:
            super().__init__(
                agent_name=agent_name,
                uuid_str=uuid_str,
                agent_profile=agent_profile,
            )
            self.model_name = model_name
            self.client = ExternalContestantClient(command, timeout_seconds=timeout_seconds)
            self._episode_id = ""
            self._previous_action = ""
            self._goal = None

        async def aact(self, obs: Observation) -> AgentAction:  # type: ignore[name-defined]
            self.recv_message("Environment", obs)
            if not self._episode_id or obs.turn_number == 0:
                self._episode_id = uuid4().hex
                profile = getattr(self, "profile", None)
                self.client.begin_episode(
                    benchmark_id="sotopia",
                    episode_id=self._episode_id,
                    title="SOTOPIA social interaction",
                    metadata={
                        "agent_name": self.agent_name,
                        "profile_id": getattr(profile, "pk", None),
                        "goal": self._goal,
                    },
                )
            elif self._previous_action:
                self.client.outcome(
                    action=self._previous_action,
                    outcome=obs.to_natural_language(),
                    public_state={"turn_number": obs.turn_number},
                )

            available = [str(x) for x in obs.available_actions]
            if available == ["none"]:
                action = AgentAction(action_type="none", argument="", to=[])
                self._previous_action = action.to_natural_language()
                return action

            turn = self.client.tool_turn(
                observation=obs.to_natural_language(),
                instruction=(
                    f"Pursue your SOTOPIA goal: {self._goal or ''}. "
                    f"Follow the environment action instruction: {obs.action_instruction}"
                ),
                tools=action_tools(available),
                context={
                    "agent_name": self.agent_name,
                    "turn_number": obs.turn_number,
                    "available_actions": available,
                },
            )
            if turn.get("kind") == "final":
                if "speak" not in available:
                    raise ValueError("Ferro returned final text when SOTOPIA has no speak action")
                action_type = "speak"
                argument = str(turn.get("response") or "")
            else:
                action_type = str(turn.get("tool_name") or "")
                if action_type not in available:
                    raise ValueError(f"Ferro chose unavailable SOTOPIA action {action_type!r}")
                arguments = turn.get("arguments")
                arguments = arguments if isinstance(arguments, Mapping) else {}
                argument = str(arguments.get("argument") or "")
            if action_type not in {"speak", "non-verbal communication", "action"}:
                argument = ""
            action = AgentAction(action_type=action_type, argument=argument, to=[])
            self._previous_action = action.to_natural_language()
            return action

        def act(self, obs: Observation) -> AgentAction:  # type: ignore[name-defined]
            raise RuntimeError("SOTOPIA Ferro agent requires async aact")

        def reset(self) -> None:
            super().reset()
            self._episode_id = ""
            self._previous_action = ""

        def close(self) -> None:
            self.client.close()

    FerroSotopiaAgent.__name__ = "FerroSotopiaAgent"
    return FerroSotopiaAgent


def run_sotopia_benchmark(
    contestant_command: Sequence[str],
    *,
    models: Sequence[str] = ("ferro-awe",),
    partner_model: str = "together_ai/meta-llama/Llama-3-70b-chat-hf",
    evaluator_model: str = "gpt-4o",
    batch_size: int = 10,
    task: str = "hard",
    url: str = "",
    output_to_jsonl: bool = True,
    push_to_db: bool = False,
    save_dir: str = ".",
    tag: str = "",
    timeout_seconds: float = 90.0,
) -> None:
    """Run the upstream SOTOPIA benchmark with Ferro as the test agent."""
    try:
        from sotopia.cli.benchmark.benchmark import _benchmark_impl
    except ImportError as exc:
        raise RuntimeError("SOTOPIA upstream package is not installed") from exc

    agent_class = build_sotopia_agent_class(
        contestant_command,
        timeout_seconds=timeout_seconds,
    )
    _benchmark_impl(
        models=list(models),
        agent_class=agent_class,
        partner_model=partner_model,
        evaluator_model=evaluator_model,
        batch_size=int(batch_size),
        task=task,
        url=url,
        print_logs=False,
        only_show_performance=False,
        output_to_jsonl=bool(output_to_jsonl),
        push_to_db=bool(push_to_db),
        save_dir=save_dir,
        tag=tag,
    )


def build_lifelong_sotopia_reproduction_agent_class(
    contestant_command: Sequence[str],
    *,
    timeout_seconds: float = 90.0,
):
    """Build a persistent-state SOTOPIA agent for Lifelong-SOTOPIA reproduction.

    The returned agent keeps the same external Ferro contestant process across
    reset() calls, so evaluation memories and self-state persist across episodes.
    This is a methodology reproduction, not an official Lifelong-SOTOPIA score.
    """
    return build_sotopia_agent_class(
        contestant_command,
        timeout_seconds=timeout_seconds,
    )
