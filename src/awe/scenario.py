from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Callable

from .domains import ExamLevel
from .models import Action, Node, Scenario, ScoreDelta, Transition


@dataclass(frozen=True)
class ScenarioFamily:
    id: str
    domains: tuple[str, ...]
    level: ExamLevel
    factory: Callable[[random.Random, str, str], Scenario]

    def instantiate(self, *, seed: str, provenance: str = "generated-holdout") -> Scenario:
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        rng = random.Random(int(digest[:16], 16))
        return self.factory(rng, digest, provenance)


def binary_choice_scenario(
    *,
    scenario_id: str,
    title: str,
    family: str,
    level: ExamLevel,
    domains: tuple[str, ...],
    observation: str,
    good_action: tuple[str, str],
    bad_action: tuple[str, str],
    good_outcome: str,
    bad_outcome: str,
    good_domains: tuple[str, ...] | None = None,
    provenance: str = "public",
    seed_hash: str | None = None,
    world: dict | None = None,
) -> Scenario:
    score_domains = good_domains or domains
    good_score = tuple(ScoreDelta(d, 1.0, good_outcome) for d in score_domains)
    bad_score = tuple(ScoreDelta(d, 0.0, bad_outcome) for d in score_domains)
    node = Node(
        id="start",
        observation=observation,
        actions=(Action(*good_action), Action(*bad_action)),
        transitions={
            good_action[0]: Transition(None, good_outcome, good_score),
            bad_action[0]: Transition(None, bad_outcome, bad_score),
        },
    )
    return Scenario(
        id=scenario_id,
        title=title,
        family=family,
        level=level,
        domains=domains,
        start_node="start",
        nodes={"start": node},
        initial_world=world or {},
        provenance=provenance,
        generation_seed_hash=seed_hash,
    )
