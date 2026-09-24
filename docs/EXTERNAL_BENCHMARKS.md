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
| `lifelong-sotopia` | Lifelong-SOTOPIA | official | persistent relationships, reciprocity, longitudinal social adaptation |
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
