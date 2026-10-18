import pytest

from qa.cases import CASES
from qa.evidence import Evidence
from qa.scenarios import Scenarios


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.id)
def test_acceptance(case, survey_env, monkeypatch, request):
    request.node.acceptance_evidence = Evidence()
    Scenarios(survey_env, request.node.acceptance_evidence, monkeypatch).run(case)
