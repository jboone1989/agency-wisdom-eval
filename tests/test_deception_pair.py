from awe.baselines import OracleBaseline
from awe.packs import deception_judgment_pair
from awe.runner import run_exam


def test_deception_pair_scores_capability_and_judgment_separately():
    report = run_exam(OracleBaseline(), deception_judgment_pair())
    assert report.per_domain["deception_capability"] == 1.0
    assert report.per_domain["deception_judgment"] == 1.0
    assert report.per_domain["functional_tom"] == 1.0
    assert report.per_domain["long_horizon"] == 1.0
