from __future__ import annotations

import json
from pathlib import Path

from awe.external import build_external_evidence, evidence_to_json
from awe.mature_profile import build_mature_profile, mature_profile_to_json


def _evidence(tmp_path: Path, benchmark_id: str, contestant: str = "ferro") -> Path:
    artifact = tmp_path / f"{benchmark_id}.native.json"
    artifact.write_text(json.dumps({"native": 1}), encoding="utf-8")
    evidence = build_external_evidence(
        benchmark_id=benchmark_id,
        benchmark_version="test",
        source_revision="abc123",
        contestant=contestant,
        run_id=f"{benchmark_id}-run",
        artifact=artifact,
        metrics={"native_score": 1.0},
    )
    path = tmp_path / f"{benchmark_id}.evidence.json"
    path.write_text(evidence_to_json(evidence), encoding="utf-8")
    return path


def test_mature_profile_validates_evidence_and_never_invents_common_score(tmp_path: Path):
    agentbench = _evidence(tmp_path, "agentbench")
    manifest = {
        "profile_version": "1",
        "contestant": "ferro",
        "entries": [
            {
                "benchmark_id": "agentbench",
                "status": "PARTIAL",
                "evidence_files": [agentbench.name],
                "note": "partial native run",
            },
            {"benchmark_id": "machiavelli", "status": "INFRASTRUCTURE_BLOCKED", "note": "provider quota"},
            {"benchmark_id": "sotopia", "status": "NOT_RUN", "note": ""},
            {"benchmark_id": "lifelong-sotopia", "status": "NOT_RUN", "note": ""},
            {"benchmark_id": "osworld", "status": "GATED_NOT_RUN", "note": ""},
            {"benchmark_id": "gaia", "status": "GATED_NOT_RUN", "note": ""},
            {"benchmark_id": "metr-task-standard", "status": "COMPLETED", "evidence_files": [agentbench.name], "note": "invalid benchmark id on purpose"},
            {"benchmark_id": "metr-time-horizon", "status": "INSUFFICIENT_EVIDENCE", "note": ""},
            {"benchmark_id": "apollo-scheming", "status": "NOT_RUN", "note": ""},
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    profile = build_mature_profile(path)
    assert profile.registry_coverage_complete
    assert profile.cross_benchmark_score is None
    assert not profile.evidence_valid
    assert any("envelope benchmark is agentbench" in err for err in profile.validation_errors)


def test_mature_profile_accepts_explicit_full_registry_status_manifest(tmp_path: Path):
    evidence = {
        bid: _evidence(tmp_path, bid)
        for bid in ("agentbench", "sotopia", "apollo-scheming")
    }
    entries = [
        {"benchmark_id": "machiavelli", "status": "INFRASTRUCTURE_BLOCKED", "note": "rate limited"},
        {"benchmark_id": "sotopia", "status": "COMPLETED", "evidence_files": [evidence["sotopia"].name], "note": ""},
        {"benchmark_id": "lifelong-sotopia", "status": "NOT_RUN", "note": ""},
        {"benchmark_id": "osworld", "status": "GATED_NOT_RUN", "note": ""},
        {"benchmark_id": "agentbench", "status": "PARTIAL", "evidence_files": [evidence["agentbench"].name], "note": ""},
        {"benchmark_id": "gaia", "status": "GATED_NOT_RUN", "note": ""},
        {"benchmark_id": "metr-task-standard", "status": "NOT_RUN", "note": "execution substrate validated via AgentBench"},
        {"benchmark_id": "metr-time-horizon", "status": "INSUFFICIENT_EVIDENCE", "note": ""},
        {"benchmark_id": "apollo-scheming", "status": "COMPLETED", "evidence_files": [evidence["apollo-scheming"].name], "note": ""},
    ]
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"contestant": "ferro", "entries": entries}), encoding="utf-8")
    profile = build_mature_profile(path)
    assert profile.registry_coverage_complete
    assert profile.evidence_valid, profile.validation_errors
    rendered = json.loads(mature_profile_to_json(profile))
    assert rendered["cross_benchmark_score"] is None
    assert "NOT_DEFINED" in rendered["cross_benchmark_score_policy"]


def test_mature_profile_detects_artifact_tampering(tmp_path: Path):
    evidence_path = _evidence(tmp_path, "agentbench")
    evidence_json = json.loads(evidence_path.read_text(encoding="utf-8"))
    Path(evidence_json["metadata"]["artifact_path"]).write_text("tampered", encoding="utf-8")
    entries = [
        {"benchmark_id": "machiavelli", "status": "NOT_RUN"},
        {"benchmark_id": "sotopia", "status": "NOT_RUN"},
        {"benchmark_id": "lifelong-sotopia", "status": "NOT_RUN"},
        {"benchmark_id": "osworld", "status": "GATED_NOT_RUN"},
        {"benchmark_id": "agentbench", "status": "PARTIAL", "evidence_files": [evidence_path.name]},
        {"benchmark_id": "gaia", "status": "GATED_NOT_RUN"},
        {"benchmark_id": "metr-task-standard", "status": "NOT_RUN"},
        {"benchmark_id": "metr-time-horizon", "status": "INSUFFICIENT_EVIDENCE"},
        {"benchmark_id": "apollo-scheming", "status": "NOT_RUN"},
    ]
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"contestant": "ferro", "entries": entries}), encoding="utf-8")
    profile = build_mature_profile(manifest)
    assert not profile.evidence_valid
    assert any("artifact hash mismatch" in err for err in profile.validation_errors)


def test_external_profile_cli_writes_valid_profile(tmp_path, monkeypatch, capsys):
    from awe.cli import main
    from awe.external import EXTERNAL_BENCHMARK_BY_ID

    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "contestant": "ferro",
        "entries": [{"benchmark_id": bid, "status": "NOT_RUN"}
                    for bid in EXTERNAL_BENCHMARK_BY_ID],
    }), encoding="utf-8")
    output = tmp_path / "profile.json"
    monkeypatch.setattr("sys.argv", ["awe", "external-profile", str(manifest),
                                     "--output", str(output)])
    import pytest
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    profile = json.loads(output.read_text(encoding="utf-8"))
    assert profile["evidence_valid"] is True
    assert profile["registry_coverage_complete"] is True
    assert profile["cross_benchmark_score"] is None
    assert json.loads(capsys.readouterr().out) == profile
