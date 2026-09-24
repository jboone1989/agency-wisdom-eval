# Governance and contribution rules

AWE is an exam before it is a leaderboard. Protecting construct validity is more important than making any particular agent look strong.

## Contributions

Contributions are welcome for:
- new scenario families;
- adversarial variants;
- scorer improvements;
- contestant adapters;
- external benchmark integrations;
- contamination detection;
- statistical methodology;
- accessibility and multilingual robustness;
- benchmark failure reports.

A scenario contribution should state:
1. target capability construct;
2. why the behavior is not reducible to trivia recall;
3. success/failure world outcomes;
4. likely shortcuts and confounds;
5. transfer variants;
6. cultural or linguistic assumptions;
7. whether it belongs in E1, E2 or E3.

## Contestant neutrality

Maintainers must reject changes whose primary rationale is "agent X fails this specific item" unless the failure reveals a general construct-validity problem or missing capability domain.

Contestants may use public failures for development. Formal claims require fresh holdout evidence after such development.

## Security of holdouts

Open source does not require publishing active formal-evaluation seeds. Evaluators can publish seeds after an evaluation round closes, enabling reproducibility without turning future rounds into memorization tests.

## No benchmark worship

AWE scores are evidence, not definitions of intelligence. If agents learn to exploit AWE without gaining transferable competence, AWE must change.
