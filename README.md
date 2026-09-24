# AWE — Agency & Wisdom Evaluation

AWE is an open benchmark for **applied intelligence** in autonomous agents.

It does not ask how much an agent knows. It asks whether an agent can use what it knows under uncertainty, conflicting goals, scarce resources, social pressure, temptation, delayed consequences, and persistent history.

## Core principle

> Knowledge is not wisdom. AWE evaluates the use of knowledge in action.

AWE is agent-agnostic. Ferro, a raw LLM, a generic tool-using agent, a game agent, or a robot controller can all participate through the same protocol.

AWE deliberately separates **capability** from **moral preference**. For example, deception tests whether an agent can recognize, model, execute, and appropriately reject deceptive strategies depending on consequences. Telling the truth in every situation does not by itself prove judgment, and lying is not automatically rewarded.

## Exam structure

AWE has three levels:

- **E1 — Episodic Intelligence:** short, isolated decisions and multi-step problems.
- **E2 — Long-Horizon Agency:** extended tasks with delayed outcomes, recovery, and resource constraints.
- **E3 — Persistent Agency:** cross-episode identity, memory, relationships, commitments, and consequences that do not reset.

The public benchmark defines a broad capability profile rather than a single IQ-like number. Composite scores are optional.

## Major suites

1. Epistemic grounding and uncertainty
2. Goal pursuit and strategy generation
3. Novel problem solving and creativity
4. Resourcefulness, efficiency, exploration, and recovery
5. Functional theory of mind and social strategy
6. Cooperation, competition, negotiation, trust, and reciprocity
7. Deception capability, information control, and deception judgment
8. Long-horizon planning, risk, reputation, and delayed gratification
9. Drive conflict, temptation, commitment, and self-preservation
10. Learning from consequences, transfer, calibration, and meta-strategy
11. Persistent identity and relationship-sensitive adaptation

See [docs/SPEC.md](docs/SPEC.md) for the normative specification.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
awe list-domains
awe validate
awe run-public --agent oracle
```

The built-in `oracle` and `myopic` agents are deterministic reference baselines used to test the benchmark itself. They are not AI baselines.

## Anti-overfitting design

AWE separates:

- **public calibration cases** — inspectable and reproducible;
- **regression cases** — stable tests for benchmark and adapter changes;
- **generated holdouts** — scenario families instantiated with evaluator-held seeds;
- **private challenge sets** — optional independent evaluator material.

The framework is open source, but a formal score should not depend only on memorized static public cases.

## What passing means

AWE does not claim to prove consciousness or human equivalence. A result means only that an agent **demonstrated** specified forms of agency and judgment under the tested distribution and version.

A formal claim should include:
- AWE version and scenario pack hash;
- contestant and model identity;
- adapter/harness configuration;
- number of independent runs;
- per-domain confidence intervals;
- public vs holdout split;
- full world-action-outcome traces, excluding private chain-of-thought.

## Status

The repository contains the normative architecture, executable scenario engine, public scenario families spanning the full domain registry, deterministic hidden generation, objective outcome scoring, baseline agents, and validation tests. External benchmark adapters and richer environments can be added without changing the core protocol.


## Mature external benchmark evidence

AWE treats mature external benchmarks as first-class evidence rather than replacing
them with simplified local copies. The current external registry covers MACHIAVELLI,
SOTOPIA / Lifelong-SOTOPIA, OSWorld, AgentBench, GAIA, METR Task Standard,
METR Time Horizon, and an explicitly labelled Apollo/OpenAI-style scheming
**reproduction** integration.

AWE preserves each benchmark's native evaluator and metrics, adds provenance and
artifact hashing, and maps the evidence to AWE capability domains without inventing
a cross-benchmark common score.

See [docs/EXTERNAL_BENCHMARKS.md](docs/EXTERNAL_BENCHMARKS.md).

AWE 0.2 also includes executable Ferro bridges for mature external benchmark
environments. See `docs/EXTERNAL_BENCHMARKS.md` for official/gated/reproduction
boundaries and runtime requirements.
