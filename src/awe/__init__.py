"""AWE — Agency & Wisdom Evaluation."""

__version__ = "0.2.0"

from .domains import DOMAINS, DomainSpec, ExamLevel
from .external import EXTERNAL_BENCHMARKS, ExternalBenchmarkSpec, ExternalEvidence, IntegrationMode
from .models import AgentDecision, ExamReport, Scenario
from .profile import AgencyEvidenceProfile, DomainEvidence

__all__ = [
    "DOMAINS",
    "DomainSpec",
    "ExamLevel",
    "AgentDecision",
    "ExamReport",
    "Scenario",
    "EXTERNAL_BENCHMARKS",
    "ExternalBenchmarkSpec",
    "ExternalEvidence",
    "IntegrationMode",
    "AgencyEvidenceProfile",
    "DomainEvidence",
]
