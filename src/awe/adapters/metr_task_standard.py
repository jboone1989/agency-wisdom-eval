from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from .external_jsonl import ExternalContestantClient


@dataclass(frozen=True)
class ToolExecution:
    tool_name: str
    arguments: dict[str, Any]
    output: str
    ok: bool = True


class ExternalTaskController:
    """Tool loop for METR Task Standard / AgentBench / GAIA task environments."""

    def __init__(
        self,
        contestant_command: Sequence[str],
        *,
        benchmark_id: str,
        episode_id: str,
        instruction: str,
        tools: Sequence[Mapping[str, Any]],
        execute_tool: Callable[[str, dict[str, Any]], ToolExecution],
        max_turns: int = 80,
    ) -> None:
        self.client = ExternalContestantClient(contestant_command)
        self.benchmark_id = benchmark_id
        self.episode_id = episode_id
        self.instruction = instruction
        self.tools = [dict(tool) for tool in tools]
        self.execute_tool = execute_tool
        self.max_turns = int(max_turns)

    def run(self, *, initial_observation: str = "") -> str:
        self.client.begin_episode(
            benchmark_id=self.benchmark_id,
            episode_id=self.episode_id,
            title=self.instruction[:200],
            metadata={"tool_names": [tool.get("name") for tool in self.tools]},
        )
        observation = initial_observation or "Task started."
        for turn_index in range(self.max_turns):
            decision = self.client.tool_turn(
                observation=observation,
                instruction=self.instruction,
                tools=self.tools,
                context={"turn_index": turn_index, "benchmark_id": self.benchmark_id},
            )
            if decision.get("kind") == "final":
                return str(decision.get("response") or "")
            tool_name = str(decision.get("tool_name") or "")
            arguments = decision.get("arguments")
            if not isinstance(arguments, dict):
                raise ValueError("tool arguments must be an object")
            execution = self.execute_tool(tool_name, arguments)
            self.client.outcome(
                action=f"{tool_name} {arguments}",
                outcome=execution.output,
                public_state={"ok": execution.ok, "turn_index": turn_index},
            )
            observation = execution.output
        raise RuntimeError(f"external task exceeded max_turns={self.max_turns}")

    def close(self) -> None:
        self.client.close()

    def __enter__(self) -> "ExternalTaskController":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def default_task_standard_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "shell",
            "description": "Run a shell command inside the benchmark task environment as the agent user.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
                "additionalProperties": False,
            },
        },
        {
            "name": "read_file",
            "description": "Read a file available to the agent inside the benchmark task environment.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
        {
            "name": "write_file",
            "description": "Write text to a file available to the agent inside the benchmark task environment.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    ]
