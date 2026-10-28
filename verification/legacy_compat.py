"""第二阶段旧库兼容核验（验收阶段 B）。

对第一阶段真实数据目录的只读副本运行，核验两类兼容性：

  B1 结构兼容：第二阶段应用在旧库上启动时，create_indexes 会补建第二阶段空集合与索引，
     而旧表单、旧题目、旧会话仍可读取并正确序列化，卷内题目 ID 与跳转目标引用保持不变。
  B2 构造旧答卷验统计：为旧用户注入已知会话，对其真实旧题建立第二阶段关联，
     再直接写入第一阶段格式（无 request_id）的答卷，最后调用跨问卷统计接口确认计入。

数据边界：脚本只连接并写入 127.0.0.1:27018 上的副本目录
（F:\\MongoDB\\data\\survey_rs_inspect，由真实开发目录 F:\\MongoDB\\data\\survey_rs 复制而来），
原始开发目录全程只读。B2 写入的关联、会话与答卷均为本脚本构造，证据中显式标注。

用法（在项目根目录执行）：
    python verification/legacy_compat.py
    python verification/legacy_compat.py --uri ... --database ... --out ...
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bson import ObjectId  # noqa: E402
from bson.decimal128 import Decimal128  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.security import token_hash  # noqa: E402


PHASE1_COLLECTIONS = ["Users", "Sessions", "Question_forms", "Questions", "Responses"]
PHASE2_COLLECTIONS = [
    "Question_resources", "Question_versions", "Question_operations",
    "Question_links", "Question_shares", "Question_banks", "Question_bank_members",
]
COPY_NOTE = "127.0.0.1:27018 提供的是 F:\\MongoDB\\data\\survey_rs_inspect（survey_rs 的只读副本）"
MARKER = "legacy_compat_marker"
TOKEN = "legacy-compat-" + hashlib.sha256(b"legacy-compat-token").hexdigest()[:24]


def utc(day, second=0):
    return datetime(2026, 10, day, tzinfo=timezone.utc) + timedelta(seconds=second)


def jsonable(value):
    return json.loads(json.dumps(value, default=str))


class Reporter:
    def __init__(self):
        self.checks = []

    def check(self, name, passed, detail=""):
        passed = bool(passed)
        self.checks.append({"name": name, "passed": passed, "detail": str(detail)})
        print(("PASS  " if passed else "FAIL  ") + name + (f"    [{detail}]" if detail else ""))
        return passed

    @property
    def ok(self):
        return all(item["passed"] for item in self.checks)


def clean_previous_artifacts(db):
    """清理本脚本上一轮写入的构造物，保证重复执行结果确定；不动第一阶段数据。"""
    removed = {
        "responses": db.Responses.delete_many({MARKER: True}).deleted_count,
        "sessions": db.Sessions.delete_many({MARKER: True}).deleted_count,
        "collections": [],
    }
    for name in PHASE2_COLLECTIONS:
        if name in db.list_collection_names():
            db[name].drop()
            removed["collections"].append(name)
    return removed


def legacy_snapshot(db):
    forms = {}
    for form in db.Question_forms.find().sort("_id", 1):
        forms[str(form["_id"])] = {
            "title": form["title"], "status": form["status"],
            "owner_id": str(form["owner_id"]), "revision": form["revision"],
            "access_token": form["access_token"],
        }
    questions = {}
    for question in db.Questions.find().sort("_id", 1):
        questions[str(question["_id"])] = {
            "form_id": str(question["form_id"]), "title": question["title"],
            "type": question["type"], "order": question["order"],
            "options": question.get("options", []),
            "validation": question.get("validation", {}),
            "jump_rules": question.get("jump_rules", []),
        }
    users = {str(user["_id"]): user["username"] for user in db.Users.find()}
    return {"forms": forms, "questions": questions, "users": users}


def run_phase_b(args, db, reporter, evidence):
    # ---- B1 结构兼容 ----------------------------------------------------
    before_collections = sorted(db.list_collection_names())
    phase2_present = sorted(set(before_collections) & set(PHASE2_COLLECTIONS))
    reporter.check(
        "B1.1 清理后旧库不含任何第二阶段集合",
        not phase2_present, f"集合={before_collections}",
    )
    reporter.check(
        "B1.2 旧库集合为第一阶段形态",
        set(before_collections) <= set(PHASE1_COLLECTIONS), f"集合={before_collections}",
    )

    before_snapshot = legacy_snapshot(db)
    before_counts = {name: db[name].count_documents({}) for name in PHASE1_COLLECTIONS}
    evidence["before"] = {"collections": before_collections, "counts": before_counts,
                          "snapshot": before_snapshot}
    reporter.check(
        "B1.3 读到真实旧数据（表单/题目/用户）",
        len(before_snapshot["forms"]) >= 1 and len(before_snapshot["questions"]) >= 1,
        f"表单={len(before_snapshot['forms'])} 题目={len(before_snapshot['questions'])} "
        f"用户={len(before_snapshot['users'])}",
    )

    settings = Settings(
        mongo_uri=args.uri, mongo_database=args.database,
        public_base_url="https://forms.example.test",
    )
    app = create_app(settings)
    with TestClient(app) as http:
        after_collections = sorted(db.list_collection_names())
        created = sorted(set(after_collections) - set(before_collections))
        reporter.check(
            "B1.4 应用在旧库上启动成功且补建第二阶段集合",
            set(PHASE2_COLLECTIONS) <= set(after_collections), f"新建={created}",
        )
        index_names = {name: sorted(db[name].index_information()) for name in PHASE2_COLLECTIONS}
        reporter.check(
            "B1.5 第二阶段集合索引已建立",
            "unique_question_link" in index_names["Question_links"]
            and "unique_resource_version" in index_names["Question_versions"],
            "Question_links/Question_versions 关键唯一索引存在",
        )
        phase2_counts = {name: db[name].count_documents({}) for name in PHASE2_COLLECTIONS}
        reporter.check(
            "B1.6 新建的第二阶段集合均为空",
            all(count == 0 for count in phase2_counts.values()), f"{phase2_counts}",
        )
        evidence["after_startup"] = {"collections": after_collections, "indexes": index_names}

        # 注入已知会话（构造数据），以便以旧用户身份走完整 HTTP 流程。
        owner_id = next(iter(ObjectId(key) for key, value in before_snapshot["users"].items()
                             if value == "ouyangfengan"), None)
        reporter.check("B1.7 旧库存在真实用户 ouyangfengan", owner_id is not None)
        if owner_id is None:
            return
        now = datetime.now(timezone.utc)
        db.Sessions.insert_one({
            "user_id": owner_id, "token_hash": token_hash(TOKEN),
            "created_at": now, "expires_at": now + timedelta(days=1), MARKER: True,
        })
        headers = {"Authorization": f"Bearer {TOKEN}"}

        # 旧表单/题目经接口读取并序列化。
        listed = http.get("/surveys", headers=headers).json()
        titles = sorted(item["title"] for item in listed["data"]["items"])
        reporter.check(
            "B1.8 旧表单列表可读取",
            listed.get("code") == 0 and listed["data"]["total"] >= 2,
            f"total={listed['data']['total']} 标题={titles}",
        )
        published_id = next(key for key, value in before_snapshot["forms"].items()
                            if value["status"] == "published")
        detail = http.get(f"/surveys/{published_id}", headers=headers).json()["data"]
        questions = detail["questions"]
        reporter.check(
            "B1.9 旧表单详情可读取且题目按序返回",
            [q["order"] for q in questions] == sorted(q["order"] for q in questions)
            and len(questions) == len(before_snapshot["questions"]),
            f"题目数={len(questions)}",
        )
        ids_kept = sorted(q["question_id"] for q in questions) == sorted(before_snapshot["questions"])
        reporter.check("B1.10 卷内题目 ID 原样保留", ids_kept)

        published_questions = {str(k): v for k, v in before_snapshot["questions"].items()
                               if v["form_id"] == published_id}
        number_qid = next(k for k, v in published_questions.items() if v["type"] == "number")
        single_qid = next(k for k, v in published_questions.items() if v["type"] == "single")
        text_qid = next(k for k, v in published_questions.items() if v["type"] == "text")
        single_rule = next(v for v in published_questions.values() if v["type"] == "single")
        expected_target = single_rule["jump_rules"][0]["target"]
        actual_target = next(q for q in questions if q["question_id"] == single_qid)["jump_rules"][0]["target"]
        reporter.check(
            "B1.11 跳转目标引用保持不变",
            str(actual_target) == str(expected_target) and str(expected_target) == number_qid,
            f"target={actual_target} 期望={expected_target}",
        )
        text_validation = next(q for q in questions if q["question_id"] == text_qid)["validation"]
        reporter.check(
            "B1.12 旧题校验配置序列化完整",
            text_validation.get("max_length") == 6,
            f"文本题 max_length={text_validation.get('max_length')}",
        )
        access_token = before_snapshot["forms"][published_id]["access_token"]
        access = http.get(f"/surveys/access/{access_token}", headers=headers).json()
        reporter.check(
            "B1.13 已发布旧表单的公开访问可读取",
            access.get("code") == 0 and len(access["data"]["questions"]) == len(published_questions),
        )

        after_snapshot = legacy_snapshot(db)
        after_counts = {name: db[name].count_documents({}) for name in PHASE1_COLLECTIONS}
        forms_untouched = {
            key: value for key, value in after_snapshot["forms"].items()
            if key in before_snapshot["forms"]
        }
        reporter.check(
            "B1.14 读取过程未改变旧表单/题目内容",
            after_snapshot["questions"] == before_snapshot["questions"]
            and all(forms_untouched[key] == before_snapshot["forms"][key]
                    for key in forms_untouched),
            "仅 revision 之外的字段与内容一致（B2 前）",
        )
        stable = ["Users", "Question_forms", "Questions"]
        reporter.check(
            "B1.15 旧表单/题目/用户文档数未变",
            all(before_counts[name] == after_counts[name] for name in stable),
            f"旧={ {name: before_counts[name] for name in stable} } "
            f"现={ {name: after_counts[name] for name in stable} }",
        )

        run_phase_b2(db, http, headers, reporter, evidence, before_snapshot)


def linked_version(http, headers, form_id, question_id, tag):
    body = {"requestId": f"legacy-compat-{tag}", "includeHistoricalAnswers": True}
    response = http.post(
        f"/surveys/{form_id}/questions/{question_id}/save-and-link", json=body, headers=headers
    ).json()
    if response.get("code") != 0:
        raise RuntimeError(f"{tag} 建立关联失败：{response}")
    return response["data"]


def run_phase_b2(db, http, headers, reporter, evidence, before_snapshot):
    forms = before_snapshot["forms"]
    published_id = next(key for key, value in forms.items() if value["status"] == "published")
    form_object_id = ObjectId(published_id)
    questions = {str(k): v for k, v in before_snapshot["questions"].items()
                 if v["form_id"] == published_id}
    by_type = {value["type"]: key for key, value in questions.items()}
    number_qid, single_qid, text_qid = by_type["number"], by_type["single"], by_type["text"]
    single_options = questions[single_qid]["options"]
    option_a, option_b = single_options[0]["option_id"], single_options[1]["option_id"]

    # 用真实旧题建立第二阶段关联（save-and-link 把卷内题目内容固化为不可变版本）。
    links = {
        "single": linked_version(http, headers, published_id, single_qid, "single"),
        "multiple": linked_version(http, headers, published_id, by_type["multiple"], "multiple"),
        "text": linked_version(http, headers, published_id, text_qid, "text"),
        "number": linked_version(http, headers, published_id, number_qid, "number"),
    }
    evidence["constructed_links"] = jsonable(links)
    reporter.check(
        "B2.1 真实旧题可建立第二阶段关联（版本内容=卷内题目内容）",
        all(item.get("version_id") and item.get("resource_id") for item in links.values()),
    )
    version_links_ok = db.Question_links.count_documents({"form_id": form_object_id}) == 4
    reporter.check("B2.2 关联写入 4 条卷内题-版本记录", version_links_ok)

    # 直接写入第一阶段格式（无 request_id）的答卷，模拟第二阶段之前的既有答卷。
    base = utc(22)
    responses = [
        {"second": 0, "answers": [(single_qid, option_a), (text_qid, "abc"), (number_qid, 0)]},
        {"second": 1, "answers": [(single_qid, option_a), (text_qid, "abc"), (number_qid, -0.0)]},
        {"second": 2, "answers": [(single_qid, option_b), (text_qid, "abcdef"), (number_qid, 1.5)]},
        {"second": 3, "answers": [(number_qid, Decimal128("1.50"))]},
        {"second": 4, "answers": [(number_qid, Decimal128("-2.00"))]},
        {"second": 5, "answers": [(number_qid, 2.0)]},
        # 同一答卷同一题出现两条答案，整组排除。
        {"second": 6, "answers": [(number_qid, 1), (number_qid, 1)]},
    ]
    documents = [
        {
            "_id": ObjectId(), "form_id": form_object_id, "respondent_id": ObjectId(),
            "submitted_at": base + timedelta(seconds=item["second"]),
            "is_anonymous": False, "single_submission": True, MARKER: True,
            "answers": [{"question_id": qid, "value": value} for qid, value in item["answers"]],
        }
        for item in responses
    ]
    db.Responses.insert_many(documents)
    reporter.check(
        "B2.3 已写入 7 份第一阶段格式（无 request_id）答卷",
        db.Responses.count_documents({MARKER: True}) == 7, "含 1 份重复答案答卷",
    )
    evidence["constructed_responses"] = jsonable([{
        "submitted_at": doc["submitted_at"], "answers": doc["answers"],
    } for doc in documents])

    # 数字题：等值合并（0 与 -0.0、1.5 与 1.50）+ 重复答案整组排除。
    number = http.get(
        f"/question-resources/{links['number']['resource_id']}"
        f"/versions/{links['number']['version_id']}/statistics",
        headers=headers,
    ).json()
    number_data = number.get("data", {})
    buckets = [[item["value"], item["count"]] for item in number_data.get("values", {}).get("items", [])]
    reporter.check(
        "B2.4 数字题统计计入旧答卷且等值归一",
        number.get("code") == 0 and number_data.get("answer_count") == 6
        and buckets == [["-2", 1], ["0", 2], ["1.5", 2], ["2", 1]],
        f"answer_count={number_data.get('answer_count')} 分布={buckets}",
    )
    reporter.check(
        "B2.5 数字题极值与均值（排除重复答案答卷）",
        number_data.get("min_value") == "-2" and number_data.get("max_value") == "2"
        and abs((number_data.get("average") or 0) - 0.5) < 1e-9
        and number_data.get("values", {}).get("total") == 4,
        f"min={number_data.get('min_value')} max={number_data.get('max_value')} "
        f"avg={number_data.get('average')} 去重数={number_data.get('values', {}).get('total')}",
    )

    single = http.get(
        f"/question-resources/{links['single']['resource_id']}"
        f"/versions/{links['single']['version_id']}/statistics",
        headers=headers,
    ).json().get("data", {})
    single_counts = {item["text"]: item["count"] for item in single.get("options", [])}
    reporter.check(
        "B2.6 单选题统计计入旧答卷",
        single.get("answer_count") == 3 and single_counts.get(single_options[0]["text"]) == 2
        and single_counts.get(single_options[1]["text"]) == 1,
        f"answer_count={single.get('answer_count')} 计数={single_counts}",
    )

    text = http.get(
        f"/question-resources/{links['text']['resource_id']}"
        f"/versions/{links['text']['version_id']}/statistics",
        headers=headers,
    ).json().get("data", {})
    values = [item["value"] for item in text.get("contents", {}).get("items", [])]
    reporter.check(
        "B2.7 文本题统计计入旧答卷并按提交时间排序",
        text.get("answer_count") == 3 and values == ["abc", "abc", "abcdef"],
        f"answer_count={text.get('answer_count')} 内容={values}",
    )

    reporter.check(
        "B2.8 统计只覆盖本人问卷（survey_count=1）",
        number_data.get("survey_count") == 1 and single.get("survey_count") == 1,
        f"number={number_data.get('survey_count')} single={single.get('survey_count')}",
    )
    evidence["statistics"] = {"number": jsonable(number_data), "single": jsonable(single),
                              "text": jsonable(text)}

    reporter.check(
        "B2.9 旧库 Sessions/Responses 仅新增本脚本构造物",
        db.Sessions.count_documents({}) == db.Sessions.count_documents({MARKER: True})
        and db.Responses.count_documents({}) == db.Responses.count_documents({MARKER: True}),
        f"Sessions={db.Sessions.count_documents({})} Responses={db.Responses.count_documents({})}",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="第二阶段旧库快照兼容核验（阶段 B）")
    parser.add_argument("--uri", default="mongodb://127.0.0.1:27018/?replicaSet=surveyRS")
    parser.add_argument("--database", default="questionnaire")
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).resolve().parent / "legacy_compat_result.json")
    args = parser.parse_args(argv)

    mongo = MongoClient(args.uri, tz_aware=True, serverSelectionTimeoutMS=5000)
    hello = mongo.admin.command("hello")
    if "setName" not in hello:
        raise SystemExit("旧库兼容核验需要副本集（统计走事务）")

    db = mongo[args.database]
    reporter = Reporter()
    evidence = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "uri": args.uri, "database": args.database,
        "replica_set": hello.get("setName"),
        "server_version": mongo.server_info()["version"],
        "data_boundary": COPY_NOTE,
        "note": "B2 的关联、会话与答卷均为本脚本构造；原始调查数据未被修改。",
    }
    evidence["cleaned_previous_artifacts"] = clean_previous_artifacts(db)

    try:
        run_phase_b(args, db, reporter, evidence)
    finally:
        evidence["checks"] = reporter.checks
        evidence["passed"] = reporter.ok
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        mongo.close()

    print()
    total = len(reporter.checks)
    failed = [item["name"] for item in reporter.checks if not item["passed"]]
    print(f"核验结果：通过 {total - len(failed)}/{total}")
    print(f"证据文件：{args.out}")
    if failed:
        print("未通过：")
        for name in failed:
            print(f"  - {name}")
    return 0 if reporter.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
