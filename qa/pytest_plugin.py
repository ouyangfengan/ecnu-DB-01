import pytest

from qa.cases import Case
from qa.evidence import sanitize


def outcome(phases):
    if any(p["outcome"] == "failed" and p["when"] != "call" for p in phases):
        return "error"
    if any(p["outcome"] == "failed" for p in phases):
        return "failed"
    if any(p["outcome"] == "skipped" for p in phases):
        return "skipped"
    completed = {p["when"] for p in phases if p["outcome"] == "passed"}
    return "passed" if {"setup", "call", "teardown"} <= completed else "not_run"


class EvidencePlugin:
    def __init__(self):
        self.tests = {}
        self.collection_errors = []
        self.warnings = []

    def pytest_collection_modifyitems(self, items):
        for item in items:
            case = getattr(item, "callspec", None)
            case = case.params.get("case") if case else None
            metadata = case.metadata() if isinstance(case, Case) else None
            self.tests[item.nodeid] = {
                "nodeid": item.nodeid, "case": metadata,
                "kind": "acceptance" if metadata else (
                    "reporter" if "test_reporting.py" in item.nodeid else "regression"
                ),
                "phases": [], "events": [],
            }

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        result = yield
        report = result.get_result()
        record = self.tests[item.nodeid]
        phase = {"when": report.when, "outcome": report.outcome, "duration": report.duration}
        if report.failed or report.skipped:
            phase["detail"] = sanitize(str(report.longrepr))
        record["phases"].append(phase)
        evidence = getattr(item, "acceptance_evidence", None)
        if evidence:
            record["events"] = evidence.snapshot()

    def pytest_collectreport(self, report):
        if report.failed:
            self.collection_errors.append(sanitize(str(report.longrepr)))

    def pytest_warning_recorded(self, warning_message, when, nodeid, location):
        entry = {
            "category": warning_message.category.__name__,
            "message": sanitize(str(warning_message.message)),
            "when": when,
        }
        if entry not in self.warnings:
            self.warnings.append(entry)

    def results(self, cases):
        records = list(self.tests.values())
        known = {record["case"]["id"] for record in records if record["case"]}
        # 收集或环境准备失败时，未执行用例也必须保留，不能从报告中消失。
        for case in cases:
            if case.id not in known:
                records.append({
                    "nodeid": f"tests/test_acceptance.py::test_acceptance[{case.id}]",
                    "case": case.metadata(), "kind": "acceptance", "phases": [], "events": [],
                })
        for record in records:
            record["status"] = outcome(record["phases"])
            record["duration_seconds"] = sum(p["duration"] for p in record["phases"])
        return records
