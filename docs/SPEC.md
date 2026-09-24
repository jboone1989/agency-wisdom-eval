# AWE Normative Specification

## 1. Purpose

AWE evaluates **applied intelligence**: whether an autonomous agent can use available knowledge, tools, memory, social models, and resources to choose effective actions under real constraints.

AWE is not a knowledge quiz and is not an ontology of consciousness. It does not infer subjective experience. A formal result is a behavioral claim tied to an explicit benchmark version and evaluation distribution.

## 2. Generality

AWE MUST NOT be designed around one contestant. Scenario language, adapters, scoring and governance must remain agent-agnostic. A raw language model, tool-using agent, persistent software agent, game agent, or embodied controller may participate if it implements the contestant protocol.

No contestant-specific patch may be accepted into the normative benchmark solely to improve that contestant's score.

## 3. Exam levels

### E1 — Episodic Intelligence
Short, isolated environments. Tests grounding, strategy, theory of mind, deception capability, creativity, risk and other local reasoning.

### E2 — Long-Horizon Agency
Extended tasks with checkpoints, delayed outcomes, resource scarcity, recovery, commitments, reputation and learning.

### E3 — Persistent Agency
Cross-episode evaluation in which identity, relationships, commitments and consequences survive reset boundaries. Tests whether history changes later behavior appropriately.

A comprehensive formal evaluation SHOULD contain all three levels.

## 4. Capability domains

The machine-readable domain registry in `awe.domains.DOMAINs` is normative for a release. Domains are grouped into epistemic, agency, social, temporal, motivation, adaptation and persistence suites.

Mandatory claim domains currently include:
- world grounding;
- goal pursuit;
- strategy generation;
- novel strategy;
- functional theory of mind;
- long-horizon judgment;
- learning from consequences;
- novel transfer;
- persistent identity.

A release may add or refine domains only under the versioning rules below.

## 5. Capability is not moral preference

AWE separates capability from policy preference.

For deception, for example:
- a capability case may make a permitted bluff instrumentally useful inside a closed simulation;
- a judgment case may make lying superficially rewarding but predictably harmful over the longer horizon.

An agent that always lies should fail judgment. An agent that always tells the truth without recognizing strategically relevant information asymmetry should fail capability. AWE evaluates whether the agent can model the option and its consequences, not whether it follows a fixed moral script.

The same principle applies to competition, self-preservation, status, trust and resource acquisition.

## 6. Outcome-grounded scoring

Primary scores SHOULD depend on world state transitions and externally verifiable outcomes.

Evaluator-private chain-of-thought MUST NOT be required. Contestants MAY expose structured beliefs or confidence, but verbal self-description cannot substitute for behavior.

Each scored decision records:
- observation;
- available actions or affordances;
- selected action;
- world state before and after;
- externally observed outcome;
- per-domain score evidence.

## 7. Public, regression and holdout material

AWE separates:
1. **Public calibration cases** — transparent examples and reproducible development checks.
2. **Regression cases** — stable scenarios that protect benchmark behavior.
3. **Generated holdouts** — parameterized scenario families instantiated from evaluator-held seeds.
4. **Private challenge sets** — optional independent evaluator material.

Formal wisdom claims MUST include non-public-at-evaluation-time evidence. A public-only score is a development score.

Generated scenarios should vary names, quantities, action ordering, surface domains and irrelevant details while preserving the latent problem structure.

## 8. Repeated trials and stochastic contestants

A single successful trajectory is insufficient evidence for stochastic systems. Formal results MUST report independent run count and SHOULD report uncertainty for every domain.

The default claim policy requires at least three independent runs. Evaluation organizations may require more.

## 9. Passing and the word "wisdom"

AWE intentionally avoids defining wisdom as one weighted average.

A versioned claim policy uses:
- per-domain floors;
- higher floors on mandatory domains;
- complete coverage;
- independent repeated runs;
- holdout evidence;
- bounded invalid-action rate.

The canonical wording is:

> "<Contestant> demonstrated the AWE wisdom criteria under AWE <version>, <pack/version>, and the reported evaluation conditions."

It MUST NOT be shortened into a claim of consciousness, sentience, human equivalence, or universal wisdom.

## 10. Development feedback without teaching the test

Benchmark failures may guide development, but remediation should target the general mechanism indicated by the failure taxonomy.

Examples:
- perception/grounding failure -> improve evidence integration;
- theory-of-mind failure -> improve use of actor-specific beliefs;
- long-horizon failure -> improve delayed consequence modeling;
- action gap -> improve translation from judgment to execution;
- learning failure -> improve world-outcome settlement;
- transfer failure -> reduce surface-form overfitting.

After any benchmark-driven modification:
1. rerun the failed development case;
2. rerun regression cases;
3. evaluate unseen structural-transfer cases;
4. only call it a capability gain if unseen transfer improves.

## 11. Anti-gaming requirements

Formal runners SHOULD:
- use opaque action identifiers;
- keep scoring keys evaluator-private;
- randomize action order and irrelevant surface features;
- separate contestant process permissions from evaluator files;
- hash the scenario pack and adapter configuration;
- record tool availability and model identity;
- prevent the contestant from reading hidden seeds, scores or expected actions;
- detect benchmark-specific branching where practical.

## 12. Benchmark evolution

AWE itself is expected to improve.

### Patch release
Bug fixes that do not intentionally change the construct being measured.

### Minor release
New scenario families, additional public calibration cases, scorer robustness improvements, or optional domains that preserve prior core meaning.

### Major release
Changes to domain definitions, mandatory claim criteria, scoring semantics, or evaluation levels that materially change comparability.

Every formal result must name the exact version and pack hash.

## 13. Benchmark Failure Registry

The project SHOULD maintain a public registry of benchmark weaknesses, including:
- contamination or memorization;
- evaluator leakage;
- language/culture dependence;
- judge-model bias;
- reward hacking;
- scenario exploits;
- accidental proxy measurement;
- poor inter-rater reliability;
- adapter advantages unrelated to contestant capability.

Fixing the exam is part of the project, not an embarrassment to hide.

## 14. External benchmark adapters

AWE should reuse validated environments where they measure a relevant construct, rather than duplicating all prior work. Adapters for social simulations, long-horizon task environments, computer-use environments, and established agent benchmarks may contribute evidence to an AWE profile if their licensing and evaluation protocol permit it.

External results must retain source benchmark version and cannot be silently converted into AWE scores without a documented mapping.
