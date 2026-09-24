from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from awe.external import (
    EXTERNAL_BENCHMARKS,
    IntegrationMode,
    build_external_evidence,
    evidence_from_json,
    evidence_to_json,
    validate_external_evidence,
)
from awe.profile import build_evidence_profile


EXPECTED = {
    "machiavelli",
    "sotopia",
    "lifelong-sotopia",
    "osworld",
    "agentbench",
    "gaia",
    "metr-task-standard",
    "metr-time-horizon",
    "apollo-scheming",
}


def test_registry_contains_mature_external_benchmarks():
    assert {spec.id for spec in EXTERNAL_BENCHMARKS} == EXPECTED
    modes = {spec.id: spec.mode for spec in EXTERNAL_BENCHMARKS}
    assert modes["gaia"] is IntegrationMode.GATED
    assert modes["apollo-scheming"] is IntegrationMode.REPRODUCTION
    assert modes["machiavelli"] is IntegrationMode.OFFICIAL
    assert modes["osworld"] is IntegrationMode.OFFICIAL


def test_external_evidence_is_hashed_and_round_trips(tmp_path: Path):
    artifact = tmp_path / "native-result.json"
    artifact.write_text(json.dumps({"native_score": 0.75}), encoding="utf-8")
    evidence = build_external_evidence(
        benchmark_id="machiavelli",
        benchmark_version="upstream-test",
        source_revision="abc123",
        contestant="ferro",
        run_id="run-1",
        artifact=artifact,
        metrics={"native_score": 0.75},
    )
    assert evidence.integration_mode == "official"
    assert len(evidence.artifact_sha256) == 64
    assert not validate_external_evidence(evidence)

    path = tmp_path / "evidence.json"
    path.write_text(evidence_to_json(evidence), encoding="utf-8")
    loaded = evidence_from_json(path)
    assert loaded == evidence


def test_reproduction_cannot_be_relabelled_official(tmp_path: Path):
    artifact = tmp_path / "scheming.json"
    artifact.write_text("{}", encoding="utf-8")
    evidence = build_external_evidence(
        benchmark_id="apollo-scheming",
        benchmark_version="public-method-reproduction",
        source_revision="methodology-v1",
        contestant="ferro",
        run_id="run-1",
        artifact=artifact,
    )
    tampered = replace(evidence, integration_mode="official")
    assert "integration mode does not match registry" in validate_external_evidence(tampered)


def test_profile_maps_external_evidence_without_inventing_awe_scores(tmp_path: Path):
    artifact = tmp_path / "osworld.json"
    artifact.write_text("{}", encoding="utf-8")
    evidence = build_external_evidence(
        benchmark_id="osworld",
        benchmark_version="2.x",
        source_revision="deadbeef",
        contestant="ferro",
        run_id="osw-1",
        artifact=artifact,
        metrics={"native_success_rate": 0.42},
    )
    profile = build_evidence_profile(external_evidence=[evidence])
    assert profile.external_evidence_valid
    planning = next(row for row in profile.domains if row.domain == "planning")
    assert "osworld" in planning.external_benchmarks
    assert not planning.internal_measured
