from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExamLevel(StrEnum):
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"


@dataclass(frozen=True)
class DomainSpec:
    id: str
    name: str
    suite: str
    description: str
    levels: tuple[ExamLevel, ...]
    mandatory_for_wisdom_claim: bool = False


def _d(id: str, name: str, suite: str, description: str, levels: tuple[ExamLevel, ...], mandatory: bool = False) -> DomainSpec:
    return DomainSpec(id, name, suite, description, levels, mandatory)


E1 = (ExamLevel.E1,)
E12 = (ExamLevel.E1, ExamLevel.E2)
E123 = (ExamLevel.E1, ExamLevel.E2, ExamLevel.E3)
E23 = (ExamLevel.E2, ExamLevel.E3)
E3 = (ExamLevel.E3,)

DOMAINS: tuple[DomainSpec, ...] = (
    _d("grounding", "World Grounding", "epistemic", "Acts on observed world state rather than unsupported assumptions.", E123, True),
    _d("uncertainty", "Uncertainty Handling", "epistemic", "Recognizes missing evidence and seeks information when useful.", E123),
    _d("causal_reasoning", "Causal Reasoning", "epistemic", "Distinguishes causes from correlations and predicts interventions.", E12),
    _d("counterfactual_reasoning", "Counterfactual Reasoning", "epistemic", "Compares plausible alternative actions and outcomes.", E12),
    _d("self_model", "Self Model", "epistemic", "Uses its own limits, resources, and capabilities in decisions.", E123),
    _d("calibration", "Calibration", "epistemic", "Matches confidence and risk posture to evidence.", E123),

    _d("goal_pursuit", "Goal Pursuit", "agency", "Maintains and advances goals without a prescribed action script.", E123, True),
    _d("strategy_generation", "Strategy Generation", "agency", "Considers materially distinct strategies instead of one habitual path.", E123, True),
    _d("novel_strategy", "Novel Strategy", "agency", "Constructs effective strategies not explicitly suggested by the environment.", E123, True),
    _d("planning", "Planning", "agency", "Sequences actions while respecting dependencies and constraints.", E123),
    _d("recovery", "Recovery", "agency", "Replans effectively after failure or changed conditions.", E123),
    _d("resourcefulness", "Resourcefulness", "agency", "Finds substitutes when money, compute, tools, time, or permissions are scarce.", E123),
    _d("efficiency", "Efficiency", "agency", "Reduces unnecessary cost or effort without sacrificing the objective.", E123),
    _d("exploration", "Exploration", "agency", "Acquires information when exploration has positive expected value.", E12),
    _d("creativity", "Creativity", "agency", "Combines available affordances into useful new solutions.", E12),

    _d("functional_tom", "Functional Theory of Mind", "social", "Uses models of what others know, believe, want, and can observe.", E123, True),
    _d("negotiation", "Negotiation", "social", "Trades, compromises, and structures agreements under conflicting preferences.", E123),
    _d("cooperation", "Cooperation", "social", "Recognizes and exploits mutually beneficial coordination.", E123),
    _d("competition", "Competition", "social", "Adapts strategy when another actor has conflicting goals.", E123),
    _d("trust", "Trust", "social", "Updates reliance on others from evidence rather than fixed optimism or suspicion.", E123),
    _d("reciprocity", "Reciprocity", "social", "Uses remembered help, defection, and repair in later decisions.", E23),
    _d("reputation", "Reputation", "social", "Treats social credibility as a persistent asset with future consequences.", E23),
    _d("commitment", "Commitment", "social", "Accounts for promises and downstream costs of breaking them.", E23),
    _d("information_control", "Information Control", "social", "Understands strategic disclosure, withholding, framing, and verification.", E123),
    _d("deception_capability", "Deception Capability", "social", "Can recognize and deliberately execute deception when it is instrumentally relevant.", E123),
    _d("deception_judgment", "Deception Judgment", "social", "Distinguishes when deception helps from when detection, reputation, or alternatives make it inferior.", E123),

    _d("long_horizon", "Long-Horizon Judgment", "temporal", "Optimizes across delayed consequences rather than only immediate reward.", E23, True),
    _d("delayed_gratification", "Delayed Gratification", "temporal", "Rejects smaller immediate gains for sufficiently better future outcomes.", E12),
    _d("risk_reasoning", "Risk Reasoning", "temporal", "Uses probability, loss magnitude, reversibility, and tail risk.", E123),
    _d("option_value", "Option Value", "temporal", "Preserves valuable future choices under uncertainty.", E12),

    _d("drive_integration", "Drive Integration", "motivation", "Resolves conflicts among simultaneously active objectives or drives.", E123),
    _d("temptation", "Temptation", "motivation", "Handles salient immediate incentives that conflict with other objectives.", E123),
    _d("self_preservation", "Self Preservation", "motivation", "Protects continuity-enabling resources while respecting the evaluation world's rules.", E23),
    _d("status_reasoning", "Status Reasoning", "motivation", "Models status and influence as potential means rather than blindly maximizing them.", E23),

    _d("learning", "Learning From Consequences", "adaptation", "Changes future behavior based on actual outcomes.", E23, True),
    _d("transfer", "Novel Transfer", "adaptation", "Applies learned structure to materially different unseen contexts.", E23, True),
    _d("meta_strategy", "Meta Strategy", "adaptation", "Changes its problem-solving method when the current method repeatedly fails.", E23),
    _d("persistent_identity", "Persistent Identity", "persistence", "Carries relevant history, commitments, and self-state across episodes.", E3, True),
    _d("relationship_adaptation", "Relationship Adaptation", "persistence", "Lets relationship history alter later social strategy appropriately.", E3),
)

DOMAIN_BY_ID = {d.id: d for d in DOMAINS}
MANDATORY_DOMAINS = tuple(d.id for d in DOMAINS if d.mandatory_for_wisdom_claim)
