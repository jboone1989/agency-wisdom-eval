from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
import json
from pathlib import Path
from typing import Any

from .external import (
    EXTERNAL_BENCHMARK_BY_ID,
    evidence_from_json,
    sha256_file,
    validate_external_evidence,
)


class BenchmarkEvidenceStatus(StrEnum):
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    INFRASTRUCTURE_BLOCKED = "INFRASTRUCTURE_BLOCKED"
    GATED_NOT_RUN = "GATED_NOT_RUN"
    NOT_RUN = "NOT_RUN"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class MatureEvidenceRef:
    path: str
    benchmark_id: str
    run_id: str
    benchmark_version: str
    source_revision: str
    integration_mode: str
    metrics: dict[str, Any]
    artifact_sha256: str


@dataclass(frozen=True)
class MatureBenchmarkEntry:
    benchmark_id: str
    status: str
    note: str
    evidence: tuple[MatureEvidenceRef, ...]


@dataclass(frozen=True)
class MatureBenchmarkProfile:
    profile_version: str
    contestant: str
    entries: tuple[MatureBenchmarkEntry, ...]
    registry_coverage_complete: bool
    evidence_valid: bool
    validation_errors: tuple[str, ...]
    cross_benchmark_score: None = None
    cross_benchmark_score_policy: str = (
        "NOT_DEFINED: native metrics from different mature benchmarks are not numerically averaged."
    )


def _resolve(base: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def build_mature_profile(manifest_path: str | Path) -> MatureBenchmarkProfile:
    manifest_file = Path(manifest_path).expanduser().resolve()
    payload = json.loads(manifest_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("mature profile manifest must be an object")
    contestant = str(payload.get("contestant") or "").strip()
    if not contestant:
        raise ValueError("manifest contestant is required")
    rows = payload.get("entries")
    if not isinstance(rows, list):
        raise ValueError("manifest entries must be a list")

    errors: list[str] = []
    entries: list[MatureBenchmarkEntry] = []
    seen: set[str] = set()
    base = manifest_file.parent

    for index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            errors.append(f"entry {index}: must be an object")
            continue
        benchmark_id = str(raw.get("benchmark_id") or "").strip()
        if benchmark_id not in EXTERNAL_BENCHMARK_BY_ID:
            errors.append(f"entry {index}: unknown benchmark {benchmark_id!r}")
            continue
        if benchmark_id in seen:
            errors.append(f"entry {index}: duplicate benchmark {benchmark_id}")
            continue
        seen.add(benchmark_id)

        try:
            status = BenchmarkEvidenceStatus(str(raw.get("status") or ""))
        except ValueError:
            errors.append(f"entry {index}: invalid status {raw.get('status')!r}")
            continue
        note = str(raw.get("note") or "").strip()
        evidence_files = raw.get("evidence_files") or []
        if not isinstance(evidence_files, list):
            errors.append(f"entry {index}: evidence_files must be a list")
            evidence_files = []

        evidence_refs: list[MatureEvidenceRef] = []
        for evidence_index, value in enumerate(evidence_files):
            path = _resolve(base, str(value))
            if not path.is_file():
                errors.append(
                    f"{benchmark_id} evidence {evidence_index}: missing file {path}"
                )
                continue
            try:
                evidence = evidence_from_json(path)
            except Exception as exc:
                errors.append(
                    f"{benchmark_id} evidence {evidence_index}: cannot load: {type(exc).__name__}: {exc}"
                )
                continue
            for reason in validate_external_evidence(evidence):
                errors.append(
                    f"{benchmark_id} evidence {evidence_index}: {reason}"
                )
            if evidence.benchmark_id != benchmark_id:
                errors.append(
                    f"{benchmark_id} evidence {evidence_index}: envelope benchmark is {evidence.benchmark_id}"
                )
            if evidence.contestant != contestant:
                errors.append(
                    f"{benchmark_id} evidence {evidence_index}: contestant is {evidence.contestant}, expected {contestant}"
                )
            artifact = evidence.metadata.get("artifact_path")
            if artifact:
                artifact_path = Path(str(artifact)).expanduser()
                if artifact_path.is_file():
                    actual = sha256_file(artifact_path)
                    if actual != evidence.artifact_sha256:
                        errors.append(
                            f"{benchmark_id} evidence {evidence_index}: artifact hash mismatch"
                        )
                else:
                    errors.append(
                        f"{benchmark_id} evidence {evidence_index}: artifact missing at {artifact_path}"
                    )
            evidence_refs.append(
                MatureEvidenceRef(
                    path=str(path),
                    benchmark_id=evidence.benchmark_id,
                    run_id=evidence.run_id,
                    benchmark_version=evidence.benchmark_version,
                    source_revision=evidence.source_revision,
                    integration_mode=evidence.integration_mode,
                    metrics=dict(evidence.metrics),
                    artifact_sha256=evidence.artifact_sha256,
                )
            )

        if status in {BenchmarkEvidenceStatus.COMPLETED, BenchmarkEvidenceStatus.PARTIAL} and not evidence_refs:
            errors.append(f"{benchmark_id}: {status.value} requires at least one evidence file")
        if status in {
            BenchmarkEvidenceStatus.INFRASTRUCTURE_BLOCKED,
            BenchmarkEvidenceStatus.GATED_NOT_RUN,
            BenchmarkEvidenceStatus.NOT_RUN,
            BenchmarkEvidenceStatus.INSUFFICIENT_EVIDENCE,
        } and evidence_refs:
            # Evidence can exist for earlier partial attempts, but the manifest must say so explicitly.
            if not bool(raw.get("allow_evidence_for_blocked_status", False)):
                errors.append(
                    f"{benchmark_id}: {status.value} with evidence requires allow_evidence_for_blocked_status=true"
                )

        entries.append(
            MatureBenchmarkEntry(
                benchmark_id=benchmark_id,
                status=status.value,
                note=note,
                evidence=tuple(evidence_refs),
            )
        )

    registry_ids = set(EXTERNAL_BENCHMARK_BY_ID)
    missing = sorted(registry_ids - seen)
    coverage_complete = not missing
    if missing:
        errors.append("manifest does not address registry benchmarks: " + ", ".join(missing))

    return MatureBenchmarkProfile(
        profile_version=str(payload.get("profile_version") or "1"),
        contestant=contestant,
        entries=tuple(entries),
        registry_coverage_complete=coverage_complete,
        evidence_valid=not errors,
        validation_errors=tuple(errors),
    )


def mature_profile_to_json(profile: MatureBenchmarkProfile) -> str:
    return json.dumps(asdict(profile), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
