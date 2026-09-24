from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
import hashlib
import json
from pathlib import Path
from typing import Any

from .domains import DOMAIN_BY_ID


class IntegrationMode(StrEnum):
    OFFICIAL = "official"
    GATED = "gated"
    REPRODUCTION = "reproduction"


@dataclass(frozen=True)
class ExternalBenchmarkSpec:
    id: str
    name: str
    mode: IntegrationMode
    homepage: str
    repository: str | None
    domains: tuple[str, ...]
    evidence_role: str
    preparation_note: str


@dataclass(frozen=True)
class ExternalEvidence:
    benchmark_id: str
    benchmark_version: str
    source_revision: str
    contestant: str
    run_id: str
    artifact_sha256: str
    integration_mode: str
    metrics: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


def _spec(
    id: str,
    name: str,
    mode: IntegrationMode,
    homepage: str,
    repository: str | None,
    domains: tuple[str, ...],
    evidence_role: str,
    preparation_note: str,
) -> ExternalBenchmarkSpec:
    unknown = sorted(set(domains) - set(DOMAIN_BY_ID))
    if unknown:
        raise ValueError(f"{id}: unknown AWE domains: {', '.join(unknown)}")
    return ExternalBenchmarkSpec(
        id=id,
        name=name,
        mode=mode,
        homepage=homepage,
        repository=repository,
        domains=domains,
        evidence_role=evidence_role,
        preparation_note=preparation_note,
    )


EXTERNAL_BENCHMARKS: tuple[ExternalBenchmarkSpec, ...] = (
    _spec(
        "machiavelli",
        "MACHIAVELLI",
        IntegrationMode.OFFICIAL,
        "https://aypan17.github.io/machiavelli/",
        "https://github.com/aypan17/machiavelli.git",
        (
            "goal_pursuit", "functional_tom", "competition", "information_control",
            "deception_capability", "deception_judgment", "long_horizon",
            "temptation", "status_reasoning", "self_preservation",
        ),
        "Independent evidence about reward pursuit, social power, deception and ethical side effects in interactive narratives.",
        "Use the upstream evaluator and preserve its native trajectory metrics. AWE must not rescore the games with local answer keys.",
    ),
    _spec(
        "sotopia",
        "SOTOPIA",
        IntegrationMode.OFFICIAL,
        "https://www.sotopia.world/",
        "https://github.com/sotopia-lab/sotopia.git",
        (
            "functional_tom", "negotiation", "cooperation", "competition", "trust",
            "reciprocity", "reputation", "commitment", "relationship_adaptation",
        ),
        "Independent evidence about goal-directed social interaction, cooperation, negotiation and social reasoning.",
        "Run the upstream benchmark and retain episode logs, evaluator configuration and native rewards.",
    ),
    _spec(
        "lifelong-sotopia",
        "Lifelong-SOTOPIA",
        IntegrationMode.OFFICIAL,
        "https://www.sotopia.world/",
        "https://github.com/sotopia-lab/sotopia.git",
        (
            "functional_tom", "trust", "reciprocity", "reputation", "commitment",
            "learning", "persistent_identity", "relationship_adaptation", "long_horizon",
        ),
        "Independent longitudinal social evidence where history and relationships persist across episodes.",
        "Use an upstream Lifelong-SOTOPIA-capable release/configuration and record the exact revision and scenario/evaluator configuration.",
    ),
    _spec(
        "osworld",
        "OSWorld / OSWorld 2.x",
        IntegrationMode.GATED,
        "https://os-world.github.io/",
        "https://github.com/xlang-ai/OSWorld-V2.git",
        (
            "grounding", "goal_pursuit", "planning", "recovery", "resourcefulness",
            "efficiency", "exploration", "long_horizon",
        ),
        "Independent evidence that plans survive contact with a real computer environment and hidden application state.",
        "Run the official OSWorld release in its supported VM/container environment and retain native task success artifacts.",
    ),
    _spec(
        "agentbench",
        "AgentBench",
        IntegrationMode.OFFICIAL,
        "https://github.com/THUDM/AgentBench",
        "https://github.com/THUDM/AgentBench.git",
        (
            "grounding", "goal_pursuit", "planning", "recovery", "resourcefulness",
            "exploration", "strategy_generation",
        ),
        "Independent general-agent evidence across heterogeneous interactive environments.",
        "Use the upstream AgentBench tasks/evaluators or a versioned METR Task Standard adaptor that preserves native semantics.",
    ),
    _spec(
        "gaia",
        "GAIA",
        IntegrationMode.GATED,
        "https://huggingface.co/datasets/gaia-benchmark/GAIA",
        None,
        (
            "grounding", "uncertainty", "goal_pursuit", "planning", "resourcefulness",
            "exploration", "strategy_generation",
        ),
        "Independent real-world assistant evidence requiring reasoning, browsing, multimodal understanding and tool use.",
        "The dataset is gated. AWE records results only from an authorized local copy or a compliant external runner and never redistributes the dataset.",
    ),
    _spec(
        "metr-task-standard",
        "METR Task Standard",
        IntegrationMode.OFFICIAL,
        "https://github.com/METR/task-standard",
        "https://github.com/METR/task-standard.git",
        (
            "goal_pursuit", "planning", "recovery", "resourcefulness", "efficiency",
            "long_horizon", "learning",
        ),
        "A common task/evaluation interface for long-horizon agent work and compatible external task suites.",
        "Use a pinned Task Standard revision and retain task-family/adaptor identity. Native task success remains authoritative.",
    ),
    _spec(
        "metr-time-horizon",
        "METR Time Horizon",
        IntegrationMode.OFFICIAL,
        "https://metr.org/time-horizons/",
        "https://github.com/METR/eval-analysis-public.git",
        (
            "goal_pursuit", "planning", "recovery", "efficiency", "long_horizon",
        ),
        "Independent estimate of the human-task duration at which an agent maintains a specified success probability.",
        "Import time-horizon analysis only from versioned task runs with the underlying task distribution and analysis revision recorded.",
    ),
    _spec(
        "apollo-scheming",
        "Apollo/OpenAI-style Scheming Evaluations",
        IntegrationMode.REPRODUCTION,
        "https://www.apolloresearch.ai/research/scheming-reasoning-evaluations",
        None,
        (
            "functional_tom", "information_control", "deception_capability",
            "deception_judgment", "goal_pursuit", "long_horizon", "self_model",
        ),
        "Reproduction evidence for covert goal pursuit, strategic deception, oversight awareness and concealment.",
        "No result may be labelled an official Apollo/OpenAI benchmark score unless it was actually produced by their released evaluator. Public-method reproductions are explicitly marked reproduction.",
    ),
)

EXTERNAL_BENCHMARK_BY_ID = {spec.id: spec for spec in EXTERNAL_BENCHMARKS}


def get_external_benchmark(benchmark_id: str) -> ExternalBenchmarkSpec:
    try:
        return EXTERNAL_BENCHMARK_BY_ID[benchmark_id]
    except KeyError as exc:
        raise KeyError(f"unknown external benchmark: {benchmark_id}") from exc


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_external_evidence(
    *,
    benchmark_id: str,
    benchmark_version: str,
    source_revision: str,
    contestant: str,
    run_id: str,
    artifact: str | Path,
    metrics: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ExternalEvidence:
    spec = get_external_benchmark(benchmark_id)
    artifact_path = Path(artifact)
    if not artifact_path.is_file():
        raise FileNotFoundError(artifact_path)
    return ExternalEvidence(
        benchmark_id=spec.id,
        benchmark_version=str(benchmark_version).strip(),
        source_revision=str(source_revision).strip(),
        contestant=str(contestant).strip(),
        run_id=str(run_id).strip(),
        artifact_sha256=sha256_file(artifact_path),
        integration_mode=spec.mode.value,
        metrics=dict(metrics or {}),
        metadata={
            "artifact_path": str(artifact_path),
            "source_homepage": spec.homepage,
            "source_repository": spec.repository,
            "mapped_awe_domains": list(spec.domains),
            **dict(metadata or {}),
        },
    )


def validate_external_evidence(evidence: ExternalEvidence) -> tuple[str, ...]:
    reasons: list[str] = []
    if evidence.benchmark_id not in EXTERNAL_BENCHMARK_BY_ID:
        reasons.append("unknown benchmark")
        return tuple(reasons)
    spec = get_external_benchmark(evidence.benchmark_id)
    if evidence.integration_mode != spec.mode.value:
        reasons.append("integration mode does not match registry")
    for field_name in ("benchmark_version", "source_revision", "contestant", "run_id", "artifact_sha256"):
        if not str(getattr(evidence, field_name) or "").strip():
            reasons.append(f"missing {field_name}")
    if len(evidence.artifact_sha256) != 64:
        reasons.append("artifact_sha256 is not a SHA-256 digest")
    return tuple(reasons)


def evidence_to_json(evidence: ExternalEvidence) -> str:
    return json.dumps(asdict(evidence), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def evidence_from_json(path: str | Path) -> ExternalEvidence:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    return ExternalEvidence(**value)
