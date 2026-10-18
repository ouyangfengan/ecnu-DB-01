import json
from collections import Counter

from qa.cases import CATEGORIES


STATUS_NAMES = {
    "passed": "通过", "failed": "失败", "error": "准备/清理错误",
    "skipped": "跳过", "not_run": "未执行或未完成",
}


def compact(value, limit=220):
    text = json.dumps(value, ensure_ascii=False, default=str)
    text = text.replace("|", "\\|").replace("\n", "\\n").replace("`", "\\`")
    return text if len(text) <= limit else text[:limit] + "…（完整值见原始 JSON）"


def summary(records):
    counts = Counter(record["status"] for record in records)
    return "；".join(f"{STATUS_NAMES[key]} {counts[key]}" for key in STATUS_NAMES if counts[key]) or "无执行记录"


def render_markdown(result, evidence_link):
    records = result["tests"]
    acceptance = [record for record in records if record["kind"] == "acceptance"]
    lines = [
        "# 测试用例与执行报告", "",
        f"- 运行编号：`{result['run_id']}`",
        f"- 开始时间（UTC）：{result['started_at']}",
        f"- 结束时间（UTC）：{result['finished_at']}",
        f"- pytest/运行器退出码：`{result['exit_code']}`",
        f"- 六类验收：共 {len(acceptance)} 条；{summary(acceptance)}。",
        f"- 原有回归：{summary([r for r in records if r['kind'] == 'regression'])}。",
        f"- 报告工具自测：{summary([r for r in records if r['kind'] == 'reporter'])}。",
        f"- [本次完整执行证据 JSON]({evidence_link})，包含每次请求、响应、检查值、pytest 节点及准备/执行/清理阶段结果。",
        "", "## 环境与执行约定", "",
        "```json", json.dumps(result["environment"], ensure_ascii=False, indent=2), "```", "",
        "使用 pytest、FastAPI TestClient 和真实 MongoDB 副本集；HTTP 在进程内经过实际路由、鉴权和业务逻辑，不需要启动 Uvicorn。",
        "每条 API 用例使用独立随机名测试库。公共前置步骤通过注册、登录接口准备 owner、reader；凭证和密码在证据中隐藏。",
        "业务时钟固定从 2100-01-01T00:00:00Z 开始，截止场景显式推进注入时钟；报告开始/结束时间是真实执行时间，不与业务时钟混用。",
        "接口正常成功为 HTTP 200/code=0；4001→HTTP 400，4010→401，4030→403，4040→404，4090→409。脚本同时断言 HTTP 和业务码。",
        "输入中的 `<form_id>`、`<q1>`、`<token>`、`<A>` 等为准备接口实际返回的 ID、问卷链接标识或选项 ID，不是登录凭证。完整实际输入及响应见逐次请求证据。",
        "错误场景返回预期错误码属于测试通过；pytest 断言失败、环境准备或清理错误、跳过和未执行均不算通过。",
        "下列实际结果只使用本次执行记录。准备请求也列出；表格过长值仅缩略展示，原始 JSON 保留完整内容。源码 SHA-256 摘要存于 JSON，可核对执行版本。",
        "", "## 分类汇总", "",
        "| 类别 | 用例数 | 本次结果 |", "| --- | ---: | --- |",
    ]
    for category in CATEGORIES.values():
        group = [r for r in acceptance if r["case"]["category"] == category]
        lines.append(f"| {category} | {len(group)} | {summary(group)} |")
    if result.get("errors"):
        lines.extend(["", "## 运行错误", "", "```text", "\n\n".join(result["errors"]), "```"])
    if result.get("warnings"):
        lines.extend(["", "## 运行警告", ""])
        for warning in result["warnings"]:
            lines.append(f"- {warning['category']}：{warning['message']}")

    for category in CATEGORIES.values():
        lines.extend(["", f"## {category}", ""])
        for record in acceptance:
            case = record["case"]
            if case["category"] != category:
                continue
            lines.extend([
                f"### {case['id']} {case['title']}", "",
                f"脚本节点：`{record['nodeid']}`", "",
                "#### 步骤", "",
            ])
            lines.extend(f"{i}. {step}" for i, step in enumerate(case["steps"], 1))
            lines.extend([
                "", "#### 输入", "", "```json",
                json.dumps(case["inputs"], ensure_ascii=False, indent=2), "```", "",
                "#### 预期输出", "",
            ])
            lines.extend(f"- {expected}" for expected in case["expected"])
            lines.extend([
                "", "#### 实际结果", "",
                f"**{STATUS_NAMES[record['status']]}**；阶段总耗时 {record['duration_seconds']:.3f} 秒。",
            ])
            if not record["events"]:
                lines.append("未取得接口执行证据；不能据此认定功能通过。")
            api = [event for event in record["events"] if event["kind"] == "api"]
            if api:
                lines.extend([
                    "", "| 证据序号 | 阶段 | 实际接口 | HTTP | code / 提示 |",
                    "| ---: | --- | --- | --- | --- |",
                ])
                for event in api:
                    response = event.get("response", {})
                    lines.append(
                        f"| {event['sequence']} | {event.get('stage', '执行')} | "
                        f"`{event['method']} {event['path']}` | {event.get('http_status', '无响应')} | "
                        f"{compact({'code': response.get('code'), 'msg': response.get('msg', event.get('error'))})} |"
                    )
            checks = [
                event for event in record["events"]
                if event["kind"] == "check" and not event["label"].startswith("请求 #")
            ]
            if checks:
                lines.extend([
                    "", "| 检查项 | 预期值 | 实际值 | 结果 |",
                    "| --- | --- | --- | --- |",
                ])
                for check in checks:
                    lines.append(
                        f"| {check['label']} | {compact(check['expected'])} | "
                        f"{compact(check['actual'])} | {'符合' if check['passed'] else '不符合'} |"
                    )
            for phase in record["phases"]:
                if phase.get("detail"):
                    lines.extend([
                        "", f"{phase['when']} 阶段详情：", "",
                        "```text", phase["detail"][:3000], "```",
                    ])
            lines.append("")

    lines.extend([
        "## 原有回归与可追溯性", "",
        "原有账号、问卷、填写和统计测试保留，不把历史通过结果当成本次结果。每个节点的本次结果列在 JSON 的 tests 中。",
        "每次运行输出到独立时间戳目录，不覆盖旧轮次的失败证据。项目根目录的同名报告仅是最近一次运行的副本。",
        "业务数据使用临时测试库，teardown 阶段记录其清理是否成功。跳过或未执行的测试没有实际成功响应，报告不会自动补写通过。",
        "",
    ])
    return "\n".join(lines)


def write_reports(root, result):
    archive = root / "测试结果" / result["run_id"]
    archive.mkdir(parents=True, exist_ok=False)
    evidence = archive / "evidence.json"
    evidence.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (archive / "report.md").write_text(render_markdown(result, "evidence.json"), encoding="utf-8")
    latest = root / "测试用例与执行报告.md"
    latest.write_text(
        render_markdown(result, evidence.relative_to(root).as_posix()), encoding="utf-8"
    )
    return latest, evidence
