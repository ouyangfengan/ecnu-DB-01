import argparse
import hashlib
import os
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pytest
from pymongo import MongoClient

from qa.cases import CASES
from qa.evidence import sanitize, utc_timestamp
from qa.pytest_plugin import EvidencePlugin
from qa.reporting import write_reports


ROOT = Path(__file__).resolve().parents[1]


def source_hashes():
    paths = [ROOT / "requirements.txt", ROOT / "pytest.ini"]
    for directory in ("app", "tests", "qa"):
        paths.extend((ROOT / directory).rglob("*.py"))
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="执行六类验收及原有回归，生成真实四部分报告")
    parser.add_argument("--scope", choices=("all", "acceptance"), default="all")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    started, start_time = utc_timestamp(), perf_counter()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:6]
    plugin = EvidencePlugin()
    errors, environment = [], {
        "python": platform.python_version(), "platform": platform.platform(),
        "pytest": version("pytest"), "fastapi": version("fastapi"),
        "pymongo": version("pymongo"), "scope": args.scope,
        "logical_clock": "2100-01-01T00:00:00+00:00（按用例显式推进）",
        "transport": "FastAPI TestClient，进程内 HTTP；真实 MongoDB 副本集",
    }
    hashes = source_hashes()
    exit_code, client = 2, None
    try:
        uri = os.getenv("TEST_MONGODB_URI")
        if not uri:
            raise RuntimeError("请设置 TEST_MONGODB_URI，指向独立测试用 MongoDB 副本集")
        client = MongoClient(
            uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000, socketTimeoutMS=10000
        )
        hello = client.admin.command("hello")
        if "setName" not in hello and hello.get("msg") != "isdbgrid":
            raise RuntimeError("本验收需要 MongoDB 副本集，不允许跳过事务测试或退回内存模拟")
        environment.update({
            "mongodb": client.server_info()["version"],
            "replica_set": hello.get("setName", "sharded"),
            "hosts": sorted(f"{host}:{port}" for host, port in client.nodes),
        })
        target = ROOT / "tests" if args.scope == "all" else ROOT / "tests" / "test_acceptance.py"
        pytest_args = [str(target), "-q", "--tb=short", "-c", str(ROOT / "pytest.ini"), "--rootdir", str(ROOT)]
        environment["pytest_arguments"] = [argument.replace(str(ROOT), "<项目根目录>") for argument in pytest_args]
        exit_code = int(pytest.main(pytest_args, plugins=[plugin]))
    except KeyboardInterrupt:
        exit_code = 130
        errors.append("运行被用户中断；未完成的用例不计为通过。")
    except Exception as error:
        errors.append(sanitize(f"{type(error).__name__}: {error}"))
    finally:
        if client is not None:
            client.close()
    records = plugin.results(CASES)
    for record in records:
        if record["kind"] != "acceptance" or record["status"] != "passed":
            continue
        checks = [event for event in record["events"] if event["kind"] == "check"]
        api = [event for event in record["events"] if event["kind"] == "api"]
        if not api or not checks or any(not check["passed"] for check in checks):
            errors.append(f"{record['nodeid']} 的通过状态与采集证据不一致。")
            record["status"] = "error"
            exit_code = 2
    if plugin.collection_errors:
        errors.extend(plugin.collection_errors)
    if source_hashes() != hashes:
        errors.append("执行期间源码发生变化，当前结果不能唯一对应一个代码版本，请重新运行。")
        exit_code = 2
    result = {
        "schema_version": 1, "run_id": run_id, "started_at": started, "finished_at": utc_timestamp(),
        "elapsed_seconds": round(perf_counter() - start_time, 3),
        "exit_code": exit_code, "environment": environment, "source_sha256": hashes,
        "errors": errors, "warnings": plugin.warnings, "tests": records,
    }
    latest, evidence = write_reports(root, result)
    print(f"\n报告：{latest}\n原始执行证据：{evidence}\n退出码：{exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
