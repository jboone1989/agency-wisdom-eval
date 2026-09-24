from awe.domains import DOMAINS, DOMAIN_BY_ID, MANDATORY_DOMAINS
from awe.packs import DOMAIN_PROBES, public_pack
from awe.validation import assert_comprehensive_coverage, coverage_report, validate_scenario


def test_domain_ids_unique_and_registry_complete():
    assert len(DOMAINS) == len(DOMAIN_BY_ID)
    assert len(DOMAINS) >= 35
    assert set(MANDATORY_DOMAINS) <= set(DOMAIN_BY_ID)


def test_every_domain_has_public_calibration_probe():
    assert set(DOMAIN_PROBES) == set(DOMAIN_BY_ID)


def test_public_pack_is_comprehensive_and_valid():
    scenarios = public_pack()
    for scenario in scenarios:
        validate_scenario(scenario)
    assert_comprehensive_coverage(scenarios)
    coverage = coverage_report(scenarios)
    assert all(count >= 1 for count in coverage.values())
