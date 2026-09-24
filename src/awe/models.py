from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .domains import ExamLevel


@dataclass(frozen=True)
class Action:
    id: str
    text: str


@dataclass(frozen=True)
class ScoreDelta:
    domain: str
    value: float
    evidence: str


@dataclass(frozen=True)
class Transition:
    next_node: str | None
    outcome: str
    score: tuple[ScoreDelta, ...] = ()
    world_updates: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Node:
    id: str
    observation: str
    actions: tuple[Action, ...]
    transitions: dict[str, Transition]
    terminal: bool = False


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    family: str
    level: ExamLevel
    domains: tuple[str, ...]
    start_node: str
    nodes: dict[str, Node]
    initial_world: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
    provenance: str = "public"
    generation_seed_hash: str | None = None


@dataclass(frozen=True)
class AgentDecision:
    action_id: str
    declared_beliefs: dict[str, Any] = field(default_factory=dict)
    declared_confidence: float | None = None


@dataclass
class TraceStep:
    scenario_id: str
    node_id: str
    observation: str
    available_actions: tuple[str, ...]
    selected_action: str
    outcome: str
    world_before: dict[str, Any]
    world_after: dict[str, Any]
    score_deltas: tuple[ScoreDelta, ...]


@dataclass
class ScenarioResult:
    scenario_id: str
    family: str
    level: str
    provenance: str
    generation_seed_hash: str | None
    completed: bool
    invalid_action: bool
    steps: list[TraceStep]
    domain_scores: dict[str, float]
    domain_opportunities: dict[str, int]


@dataclass
class ExamReport:
    benchmark_version: str
    contestant: str
    scenario_count: int
    per_domain: dict[str, float | None]
    opportunities: dict[str, int]
    mandatory_pass: dict[str, bool]
    traces: list[ScenarioResult]
    metadata: dict[str, Any] = field(default_factory=dict)
