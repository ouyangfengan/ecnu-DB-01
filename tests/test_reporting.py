import json

import pytest

from qa.cases import CASES, CATEGORIES
from qa.evidence import Evidence, sanitize
from qa.pytest_plugin import EvidencePlugin, outcome
from qa.reporting import render_markdown, write_reports


def phases(*items):
    return [{"when": when, "outcome": result, "duration": 0.01} for when, result in items]


@pytest.mark.parametrize("stages,expected", [
    ([], "not_run"),
    (phases(("setup", "passed"), ("call", "passed")), "not_run"),
    (phases(("setup", "passed"), ("call", "passed"), ("teardown", "passed")), "passed"),
    (phases(("setup", "failed"), ("teardown", "passed")), "error"),
    (phases(("setup", "passed"), ("call", "passed"), ("teardown", "failed")), "error"),
    (phases(("setup", "passed"), ("call", "failed"), ("teardown", "passed")), "failed"),
    (phases(("setup", "skipped"), ("teardown", "passed")), "skipped"),
])
def test_outcome_never_turns_incomplete_failed_or_skipped_test_into_pass(stages, expected):
    assert outcome(stages) == expected


def test_sensitive_evidence_is_redacted_recursively_without_mutating_input():
    raw = {
        "Authorization": "Bearer live-credential",
        "nested": [{"password": "private-password", "token": "private-token"}],
        "exception": "MongoClient('mongodb://user:private-db-password@host/test')",
        "failure": """json={'password': 'private-password', 'token': 'private-token'}""",
        "business": {"requestId": "legitimate-id", "value": "原始内容"},
    }
    clean = sanitize(raw)
    serialized = json.dumps(clean, ensure_ascii=False)
    for secret in ("live-credential", "private-password", "private-token", "private-db-password"):
        assert secret not in serialized
    assert clean["business"] == raw["business"]
    assert raw["nested"][0]["password"] == "private-password"


def test_failed_assertion_is_recorded_before_raising():
    evidence = Evidence()
    with pytest.raises(AssertionError):
        evidence.check("真实失败", actual=2, expected=1)
    result = evidence.snapshot()[0]
    assert result["actual"] == 2 and result["expected"] == 1 and result["passed"] is False


def test_manifest_has_unique_ids_six_categories_and_complete_definitions():
    assert len({case.id for case in CASES}) == len(CASES)
    assert {case.category for case in CASES} == set(CATEGORIES.values())
    assert all(case.steps and case.inputs and case.expected for case in CASES)


def fake_run(run_id):
    return {
        "run_id": run_id, "started_at": "2000-01-01T00:00:00Z", "finished_at": "2000-01-01T00:00:01Z",
        "exit_code": 2, "environment": {"kind": "报告工具单元测试，不是业务执行"},
        "tests": EvidencePlugin().results(CASES[:1]), "errors": ["环境不可用"], "warnings": [],
    }


def test_missing_execution_remains_not_run_with_all_four_sections():
    result = fake_run("unit-1")
    record = result["tests"][0]
    assert record["status"] == "not_run" and record["events"] == []
    text = render_markdown(result, "evidence.json")
    assert all(f"#### {heading}" in text for heading in ("步骤", "输入", "预期输出", "实际结果"))
    assert "未取得接口执行证据" in text
    assert "**通过**" not in text


def test_new_run_preserves_previous_failed_evidence(tmp_path):
    first = fake_run("unit-first")
    latest, evidence = write_reports(tmp_path, first)
    original = evidence.read_text(encoding="utf-8")
    write_reports(tmp_path, fake_run("unit-second"))
    assert evidence.read_text(encoding="utf-8") == original
    assert json.loads(original)["tests"][0]["status"] == "not_run"
    assert "unit-second" in latest.read_text(encoding="utf-8")
    assert (tmp_path / "测试结果" / "unit-first" / "report.md").is_file()
