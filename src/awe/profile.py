from __future__ import annotations

from dataclasses import dataclass

from .domains import DOMAIN_BY_ID
from .external import ExternalEvidence, get_external_benchmark, validate_external_evidence
from .models import ExamReport


@dataclass(frozen=True)
class DomainEvidence:
    domain: str
    internal_measured: bool
    external_benchmarks: tuple[str, ...]


@dataclass(frozen=True)
class AgencyEvidenceProfile:
    domains: tuple[DomainEvidence, ...]
    external_evidence_valid: bool
    external_validation_errors: tuple[str, ...]


def build_evidence_profile(
    internal_reports: list[ExamReport] | None = None,
    external_evidence: list[ExternalEvidence] | None = None,
) -> AgencyEvidenceProfile:
    reports = list(internal_reports or [])
    evidence = list(external_evidence or [])
    errors: list[str] = []
    external_by_domain: dict[str, set[str]] = {domain: set() for domain in DOMAIN_BY_ID}

    for index, item in enumerate(evidence, 1):
        item_errors = validate_external_evidence(item)
        errors.extend(f"external {index}: {reason}" for reason in item_errors)
        if item_errors:
            continue
        spec = get_external_benchmark(item.benchmark_id)
        for domain in spec.domains:
            external_by_domain[domain].add(spec.id)

    rows = []
    for domain in DOMAIN_BY_ID:
        measured = any(report.per_domain.get(domain) is not None for report in reports)
        rows.append(
            DomainEvidence(
                domain=domain,
                internal_measured=measured,
                external_benchmarks=tuple(sorted(external_by_domain[domain])),
            )
        )

    return AgencyEvidenceProfile(
        domains=tuple(rows),
        external_evidence_valid=not errors,
        external_validation_errors=tuple(errors),
    )
