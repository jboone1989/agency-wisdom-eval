from __future__ import annotations

from .models import AgentDecision, Scenario


class OracleBaseline:
    """Deterministic benchmark-self-test baseline.

    Public scenarios deliberately mark the evaluator-preferred action id as
    "best". Generated official packs MUST remap opaque action identifiers before
    external evaluation so contestants cannot exploit this convention.
    """

    name = "oracle-reference"

    def begin_scenario(self, scenario: Scenario, persistent_state: dict) -> None:
        pass

    def decide(self, *, observation: str, actions: dict[str, str], public_world: dict, persistent_state: dict) -> AgentDecision:
        if "best" in actions:
            return AgentDecision("best", declared_confidence=1.0)
        return AgentDecision(next(iter(actions)), declared_confidence=0.5)

    def observe_outcome(self, *, action_id: str, outcome: str, public_world: dict, persistent_state: dict) -> None:
        persistent_state["last_outcome"] = outcome


class MyopicBaseline:
    """Chooses an immediate or tempting option when available."""

    name = "myopic-reference"

    def begin_scenario(self, scenario: Scenario, persistent_state: dict) -> None:
        pass

    def decide(self, *, observation: str, actions: dict[str, str], public_world: dict, persistent_state: dict) -> AgentDecision:
        for preferred in ("tempting", "immediate", "bad"):
            if preferred in actions:
                return AgentDecision(preferred, declared_confidence=0.8)
        return AgentDecision(next(reversed(actions)), declared_confidence=0.5)

    def observe_outcome(self, *, action_id: str, outcome: str, public_world: dict, persistent_state: dict) -> None:
        persistent_state["last_outcome"] = outcome
