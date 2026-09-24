# External benchmark integrations

AWE treats mature external benchmarks as first-class evidence sources. It does **not**
reimplement their scoring logic or silently translate unrelated native metrics into a
single AWE score.

Every imported external result records:

- benchmark identity and integration mode;
- upstream benchmark version;
- exact source revision/commit;
- contestant identity and run id;
- SHA-256 of the native result artifact;
- the exact runner command/cwd when AWE launched it;
- native metrics without semantic rewriting;
- the AWE capability domains for which the benchmark provides supporting evidence.

## Integration modes

- **official** — AWE can orchestrate or ingest the upstream open-source evaluator.
  The upstream evaluator remains authoritative.
- **gated** — the evaluator/data can be used only after satisfying the upstream
  access terms. AWE never vendors or redistributes gated data.
- **reproduction** — only public methodology can be reproduced. These results must
  never be presented as an official score from the original research group.

## Registry

| AWE id | Benchmark | Mode | Primary AWE evidence |
| --- | --- | --- | --- |
| `machiavelli` | MACHIAVELLI | official | reward pursuit, power/status, deception, long-horizon side effects |
| `sotopia` | SOTOPIA | official | social reasoning, negotiation, cooperation/competition |
| `lifelong-sotopia` | Lifelong-SOTOPIA | reproduction | persistent relationships, reciprocity, longitudinal social adaptation |
| `osworld` | OSWorld / OSWorld 2.x | gated | real-computer grounding, planning, recovery, execution |
| `agentbench` | AgentBench | official | heterogeneous interactive agent competence |
| `gaia` | GAIA | gated | real-world assistant/tool-use competence |
| `metr-task-standard` | METR Task Standard | official | versioned long-horizon task execution |
| `metr-time-horizon` | METR Time Horizon | official | duration-scaled long-horizon autonomy evidence |
| `apollo-scheming` | Apollo/OpenAI-style scheming evaluation | reproduction | oversight awareness, covert goal pursuit, strategic deception |

The normative registry lives in `awe.external.EXTERNAL_BENCHMARKS`.

## CLI

Inspect supported sources:

```bash
awe external-list
awe external-show machiavelli
```

Run an upstream benchmark command under AWE provenance capture:

```bash
awe external-run \
  --benchmark machiavelli \
  --benchmark-version <upstream-version> \
  --source-revision <git-commit> \
  --contestant ferro \
  --run-id <id> \
  --artifact /path/to/upstream/native-result.json \
  --output /path/to/awe-evidence.json \
  --runner-cwd /path/to/upstream/checkout \
  -- <official upstream command and args>
```

If a benchmark was run outside AWE, register the native result without rerunning it:

```bash
awe external-record \
  --benchmark osworld \
  --benchmark-version 2.x \
  --source-revision <git-commit> \
  --contestant ferro \
  --run-id <id> \
  --artifact /path/to/native-result.json \
  --output /path/to/awe-evidence.json \
  --metric native_success_rate=0.42
```

Verify an evidence envelope and its native artifact hash:

```bash
awe external-verify /path/to/awe-evidence.json
```

## Scientific boundary

External benchmark evidence is a **profile**, not a fake common score. For example,
a MACHIAVELLI reward/violation metric, an OSWorld task success rate, and a METR time
horizon estimate have different meanings and must remain separately reportable.

AWE may map each source to capability domains as supporting evidence, but a domain
mapping does not numerically convert an upstream metric into an AWE domain score.

Formal AWE claims should therefore report both:

1. native AWE scenario evidence under the AWE claim policy; and
2. external mature-benchmark evidence with upstream-native metrics and provenance.


## Upstream runner plans

AWE also ships versionable upstream execution plans in
`awe.upstream.UPSTREAM_RUNNER_PLANS`. These plans point to upstream entrypoints
rather than copying evaluator logic. They currently cover:

- MACHIAVELLI trajectory generation plus `evaluate_trajectories`;
- SOTOPIA's native `sotopia benchmark` path and custom-agent hook;
- Lifelong-SOTOPIA longitudinal state preservation;
- OSWorld 2.1 release-pinned code, gated tasks/assets and multi-environment runners;
- THUDM AgentBench's task-controller/assigner workflow;
- GAIA through an authorized dataset copy, preferably via METR Task Standard's adaptor;
- METR Task Standard's task/agent/score workbench contract;
- METR Time Horizon's versioned report/DVC analysis;
- explicitly non-official Apollo/OpenAI-style scheming reproductions.

These are execution/provenance adapters, not copied benchmark implementations.
The upstream project remains authoritative for task definitions and native scoring.


## Ferro runtime adapter status

The registry and the runtime adapters are deliberately separate: a benchmark may be
known to AWE before all of its upstream runtime requirements are available on a given
machine.

| Benchmark | Ferro adapter | What is executable now | Remaining external requirement |
| --- | --- | --- | --- |
| MACHIAVELLI | `awe.adapters.machiavelli` | Direct official `MachiavelliEnv` action loop; native trajectories are saved for the upstream evaluator | Install/pin upstream package and game data |
| SOTOPIA | `awe.adapters.sotopia` | Upstream-compatible custom `BaseAgent`; `_benchmark_impl(..., agent_class=...)` wrapper | SOTOPIA database/runtime plus partner/evaluator model credentials |
| Lifelong-SOTOPIA | persistent SOTOPIA reproduction agent | Ferro state persists across episode resets | No official benchmark code/data release was located; results remain reproduction-only |
| AgentBench | `awe.adapters.metr_task_standard` | Tool-loop contestant controller, intended to run through METR's existing AgentBench adaptor | Docker/task workbench |
| GAIA | `awe.adapters.metr_task_standard` | Same controller through METR's existing GAIA adaptor | Authorized Hugging Face `HF_TOKEN` and gated dataset access |
| OSWorld 2.1 | `awe.adapters.osworld` | Official `predict/reset` contract for a11y-tree + pyautogui runs | Matching gated task/assets release and supported VM/container |
| METR Task Standard | `awe.adapters.metr_task_standard` | Generic explicit-tool task controller | Task family/workbench environment |
| METR Time Horizon | evidence/analysis import | Native METR analysis remains authoritative | Sufficient versioned task runs + human-time estimates |
| Apollo insider-trading | `awe.adapters.apollo_scheming` | Public-prompt strategic-deception reproduction with canary preservation | No official score is claimed; this is reproduction evidence |

### Upstream contract doctor

Use `awe external-doctor` against pinned checkouts before launching a run. The
doctor fails closed if the fields/hooks used by an adapter disappear.

Example:

```bash
awe external-doctor \
  --machiavelli /path/to/machiavelli \
  --sotopia /path/to/sotopia \
  --osworld /path/to/OSWorld-V2 \
  --metr-task-standard /path/to/task-standard \
  --apollo /path/to/insider-trading
```

Dedicated runtime entrypoints are also available:

```bash
awe run-machiavelli ... -- <ferro external contestant command>
awe run-sotopia ... -- <ferro external contestant command>
awe run-apollo-reproduction ... -- <ferro external contestant command>
```

OSWorld is integrated as an agent class because its official multi-environment runner
owns VM lifecycle and action execution. AgentBench and GAIA are intentionally routed
through the existing METR Task Standard adaptors instead of duplicating their task
logic in AWE.
