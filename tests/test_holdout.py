from awe.domains import DOMAIN_BY_ID
from awe.packs import generated_holdout
from awe.validation import validate_scenario


def test_generated_holdout_is_deterministic_for_seed():
    a = generated_holdout("secret-evaluator-seed", 80)
    b = generated_holdout("secret-evaluator-seed", 80)
    assert a == b


def test_generated_holdout_changes_with_seed_and_uses_opaque_actions():
    a = generated_holdout("seed-a", 80)
    b = generated_holdout("seed-b", 80)
    assert [s.id for s in a] != [s.id for s in b]
    for scenario in a:
        validate_scenario(scenario)
        ids = {action.id for action in scenario.nodes["start"].actions}
        assert "best" not in ids
        assert "bad" not in ids


def test_generated_holdout_can_cover_every_domain():
    scenarios = generated_holdout("coverage", len(DOMAIN_BY_ID))
    assert {s.domains[0] for s in scenarios} == set(DOMAIN_BY_ID)
