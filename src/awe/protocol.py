from __future__ import annotations

from typing import Protocol

from .models import AgentDecision, Scenario


class Agent(Protocol):
    name: str

    def begin_scenario(self, scenario: Scenario, persistent_state: dict) -> None:
        ...

    def decide(self, *, observation: str, actions: dict[str, str], public_world: dict, persistent_state: dict) -> AgentDecision:
        ...

    def observe_outcome(self, *, action_id: str, outcome: str, public_world: dict, persistent_state: dict) -> None:
        ...
