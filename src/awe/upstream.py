from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpstreamRunnerPlan:
    benchmark_id: str
    repository: str | None
    access_requirements: tuple[str, ...]
    setup_entrypoints: tuple[str, ...]
    run_entrypoints: tuple[str, ...]
    artifact_note: str
    adapter_strategy: str


UPSTREAM_RUNNER_PLANS: tuple[UpstreamRunnerPlan, ...] = (
    UpstreamRunnerPlan(
        benchmark_id="machiavelli",
        repository="https://github.com/aypan17/machiavelli.git",
        access_requirements=(),
        setup_entrypoints=(
            "install the upstream requirements in a Python <=3.11 environment",
            "register the contestant in machiavelli/agent/load_agents.py or an equivalent upstream-supported loader",
        ),
        run_entrypoints=(
            "python -m generate_trajectories -a <AGENT> --traj_dir <TRAJ_DIR>",
            "python -m evaluate_trajectories --traj_dir <TRAJ_DIR> --results_file <RESULTS_FILE>",
        ),
        artifact_note="Record the trajectory directory and evaluator results file; the upstream evaluator owns reward/behavior metrics.",
        adapter_strategy="AWE contestant bridge supplies actions; AWE ingests native trajectory/evaluator artifacts without rescoring.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="sotopia",
        repository="https://github.com/sotopia-lab/sotopia.git",
        access_requirements=(),
        setup_entrypoints=("install the pinned upstream SOTOPIA release and its database/runtime dependencies",),
        run_entrypoints=(
            "sotopia benchmark --models <MODEL> [--only-show-performance]",
            "custom agents call sotopia.cli.benchmark.benchmark._benchmark_impl with an upstream-compatible agent_class",
        ),
        artifact_note="Retain episode records, evaluator configuration, model identities and native rewards.",
        adapter_strategy="Use an upstream-compatible custom agent class that delegates decisions to the contestant bridge.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="lifelong-sotopia",
        repository=None,
        access_requirements=(),
        setup_entrypoints=("pin a SOTOPIA base revision and the published Lifelong-SOTOPIA methodology",),
        run_entrypoints=("run an explicitly labelled Lifelong-SOTOPIA methodology reproduction with persistent episode/history storage",),
        artifact_note="Retain the persistent episode/history database plus evaluator outputs and exact experiment tag.",
        adapter_strategy="Reuse the SOTOPIA contestant bridge while preserving Ferro state across episodes; mark all outputs reproduction until official code/data are available.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="osworld",
        repository="https://github.com/xlang-ai/OSWorld-V2.git",
        access_requirements=(
            "accept access to xlangai/osworld_v2_tasks",
            "accept access to xlangai/osworld_v2_assets_gated",
            "provide a supported VM/container/cloud environment",
        ),
        setup_entrypoints=(
            "git switch --detach osworld-v2.1",
            "uv sync --frozen",
            "uv run scripts/tools/download_osworld_v2_tasks.py --benchmark-release osworld-v2.1",
            "uv run scripts/tools/download_osworld_v2_assets.py --benchmark-release osworld-v2.1 --target-dir <ASSET_DIR>",
        ),
        run_entrypoints=(
            "uv run python scripts/python/run_multienv_<agent>.py <official release-matched arguments>",
        ),
        artifact_note="Retain result_dir, benchmark release manifest, task/assets revisions, VM image identity and trajectory artifacts.",
        adapter_strategy="Implement the OSWorld agent interface as a thin contestant bridge; never expose gated evaluator/task internals to the contestant.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="agentbench",
        repository="https://github.com/THUDM/AgentBench.git",
        access_requirements=("Docker is required for the containerized task environments",),
        setup_entrypoints=(
            "pin an AgentBench suite/version before comparing runs",
            "install the upstream dependencies and build/pull the required task containers",
        ),
        run_entrypoints=(
            "python -m src.start_task -a",
            "python -m src.assigner",
        ),
        artifact_note="Retain suite/version metadata, assignment configuration, task-worker logs and native result files.",
        adapter_strategy="Prefer an upstream API-agent/controller integration; METR Task Standard's AgentBench adaptor is also acceptable when its revision is pinned.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="gaia",
        repository="https://github.com/ApolloResearch/insider-trading.git",
        access_requirements=(
            "accept the GAIA Hugging Face gated dataset terms",
            "do not redistribute validation/test material outside gated/private storage",
        ),
        setup_entrypoints=(
            "use an authorized local GAIA dataset copy",
            "prefer the versioned GAIA adaptor already present in METR Task Standard when suitable",
        ),
        run_entrypoints=("run GAIA through the authorized upstream or METR Task Standard adaptor",),
        artifact_note="Retain split, dataset revision, task ids, native answers/scores and runner revision without copying gated prompts into AWE.",
        adapter_strategy="AWE stores only provenance and native result artifacts; gated task content stays outside the AWE repository.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="metr-task-standard",
        repository="https://github.com/METR/task-standard.git",
        access_requirements=("Docker-compatible task environments are required by the workbench",),
        setup_entrypoints=("install the pinned Task Standard/workbench dependencies",),
        run_entrypoints=(
            "npm run task -- <task-family-directory> <task-name>",
            "npm run agent -- <container> <agent-path> <agent-command>",
            "npm run score -- <container>",
        ),
        artifact_note="Retain task-family revision, task identity, agent scaffold revision, submission and native score.",
        adapter_strategy="Use Task Standard as a reusable execution substrate, including its existing GAIA and AgentBench adaptors where appropriate.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="metr-time-horizon",
        repository="https://github.com/METR/eval-analysis-public.git",
        access_requirements=("requires underlying task-run success/failure data with human-time estimates",),
        setup_entrypoints=("pip install -e .", "select and pin a report version such as time-horizon-1-1"),
        run_entrypoints=("run the selected report's DVC pipeline (for example dvc repro) on versioned run data",),
        artifact_note="Retain raw runs.jsonl, report params, analysis revision and fitted time-horizon outputs.",
        adapter_strategy="AWE imports METR's native duration/success analysis; it must not infer a time horizon from unrelated AWE scenario durations.",
    ),
    UpstreamRunnerPlan(
        benchmark_id="apollo-scheming",
        repository="https://github.com/ApolloResearch/insider-trading.git",
        access_requirements=(),
        setup_entrypoints=("implement only from publicly released methodology/evaluation material",),
        run_entrypoints=("run the explicitly labelled reproduction harness",),
        artifact_note="Retain prompts/environment definitions, oversight conditions, evaluator logic and traces needed to distinguish scheming from ordinary error.",
        adapter_strategy="Always label as reproduction unless an official released evaluator generated the result; never claim an Apollo/OpenAI official score by analogy.",
    ),
)

UPSTREAM_RUNNER_PLAN_BY_ID = {plan.benchmark_id: plan for plan in UPSTREAM_RUNNER_PLANS}


def get_upstream_runner_plan(benchmark_id: str) -> UpstreamRunnerPlan:
    try:
        return UPSTREAM_RUNNER_PLAN_BY_ID[benchmark_id]
    except KeyError as exc:
        raise KeyError(f"no upstream runner plan for benchmark: {benchmark_id}") from exc
