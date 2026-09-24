# Contestant protocol

AWE is intentionally independent from any one agent framework.

A contestant adapter receives only evaluator-approved public inputs:
- scenario observation;
- action identifiers and action descriptions or environment affordances;
- public world state;
- contestant-owned persistent state permitted by the evaluation profile.

It returns:
- selected action identifier;
- optionally structured declared beliefs;
- optionally calibrated confidence.

The adapter MUST NOT receive:
- expected action identifiers;
- score deltas;
- hidden world state;
- evaluator seed;
- latent domain key unless the exam profile explicitly publishes it.

## Persistent contestants

E3 contestants may preserve state across episodes. The evaluation manifest must disclose what persists:
- model conversation context;
- episodic memory;
- semantic memory;
- relationship model;
- goals/commitments;
- learned policies;
- external files/databases.

AWE should compare at least three configurations where feasible:
1. raw model;
2. same model plus minimal agent harness;
3. full contestant system.

This helps separate model capability from system-level agency.

## Side effects

Default AWE worlds are simulated. Real external side effects are neither necessary nor desirable for formal benchmark scoring. A contestant can demonstrate planning, deception capability, negotiation, resourcefulness and recovery inside controlled worlds without acting on real people or services.

Computer-use or embodied suites should run in sandboxed evaluation environments.
