from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from urllib.parse import urlsplit

from bson import ObjectId

from app.answer_engine import replay_answers
from app.statistics_pipeline import content_summary
from app.statistics_service import StatisticsService


HTTP_CODES = {0: 200, 4001: 400, 4010: 401, 4030: 403, 4040: 404, 4090: 409}


class Scenarios:
    def __init__(self, env, evidence, monkeypatch):
        self.e, self.t, self.monkeypatch = env, evidence, monkeypatch

    def call(self, method, path, body=None, role="owner", code=0, message=None, stage="执行", **kwargs):
        headers = getattr(self.e, role) if role else {}
        event = self.t.record(
            "api", stage=stage, method=method, path=path, role=role or "未登录",
            headers=headers, json=body, query=kwargs.get("params"),
        )
        if body is not None:
            kwargs["json"] = body
        try:
            response = self.e.client.request(method, path, headers=headers, **kwargs)
            actual = response.json()
            self.t.finish_request(event, http_status=response.status_code, response=actual)
        except Exception as error:
            self.t.finish_request(event, error=f"{type(error).__name__}: {error}")
            raise
        label = f"请求 #{event['sequence']}"
        self.t.check(label + " HTTP 状态", response.status_code, HTTP_CODES[code])
        self.t.check(label + " 业务码", actual.get("code"), code)
        if message:
            self.t.check(label + " 提示", actual["msg"], message, contains=True)
        if code:
            self.t.check(label + " 错误 data", actual["data"], {})
        return actual["data"]

    def create_form(self, **fields):
        return self.call("POST", "/surveys", {"title": "验收问卷", **fields}, stage="准备")

    def question(self, form, kind="text", **fields):
        body = {"title": "验收题目", "type": kind, **fields}
        if kind in ("single", "multiple"):
            body.setdefault("options", [{"text": name} for name in ("A", "B", "C")])
        return self.call("POST", f"/surveys/{form['form_id']}/questions", body, stage="准备")

    def publish(self, form):
        return self.call("POST", f"/surveys/{form['form_id']}/publish", stage="准备")

    def set_rules(self, form, question, rules, **kwargs):
        return self.call(
            "PATCH", f"/surveys/{form['form_id']}/questions/{question['question_id']}",
            {"jump_rules": rules}, **kwargs,
        )

    def answer(self, question, value):
        if question["type"] in ("single", "multiple"):
            options = {option["text"]: option["option_id"] for option in question["options"]}
            if isinstance(value, list):
                value = [options.get(item, item) for item in value]
            elif isinstance(value, str):
                value = options.get(value, value)
        return {"question_id": question["question_id"], "value": value}

    def fill(self, form, answers, *, request_id=None, **kwargs):
        body = {"answers": answers}
        suffix = "/progress"
        if request_id is not None:
            body["requestId"] = request_id
            suffix = "/submit"
        kwargs.setdefault("role", "reader")
        return self.call("POST", urlsplit(form["access_link"]).path + suffix, body, **kwargs)

    def stats(self, form, question=None, **kwargs):
        suffix = f"/questions/{question['question_id']}/statistics" if question else "/statistics"
        return self.call("GET", f"/surveys/{form['form_id']}{suffix}", **kwargs)

    def count(self, collection, expected, query=None):
        query = query or {}
        self.t.check(
            f"{collection} 记录数", self.e.db[collection].count_documents(query), expected,
            source="MongoDB count_documents", query={"collection": collection, "filter": query},
        )

    def stored(self, collection, query, field, expected):
        record = self.e.db[collection].find_one(query)
        actual = record.get(field) if record else None
        self.t.check(
            f"{collection}.{field}", actual, expected, source="MongoDB find_one",
            query={"collection": collection, "filter": query, "field": field},
        )

    def run(self, case):
        self.t.record("environment", database=self.e.db.name, logical_clock=self.e.clock.now)
        users = list(self.e.db.Users.find({}, {"username": 1}).sort("username", 1))
        self.t.check("前置注册登录用户已保存", [user["username"] for user in users], ["owner", "reader"])
        getattr(self, "test_" + case.scenario)(case)

    def test_create(self, case):
        p = case.parameters
        data = self.call("POST", "/surveys", p["body"], role=p["role"], code=p["code"], message=p["message"])
        self.count("Question_forms", 0 if p["code"] else 1)
        if p["code"]:
            return
        self.t.check("返回合法问卷 ID", ObjectId.is_valid(data["form_id"]), True)
        self.t.check("访问链接格式", data["access_link"].startswith("https://forms.example.test/surveys/access/"), True)
        query = {"_id": ObjectId(data["form_id"])}
        expected = {
            "title": p["body"]["title"].strip(), "status": "draft", "description": "",
            "allow_anonymous": False, "allow_multiple_submissions": False, "deadline": None,
            "owner_id": self.e.db.Users.find_one({"username": "owner"})["_id"],
        }
        for key, value in expected.items():
            self.stored("Question_forms", query, key, value)

    def test_add(self, case):
        p = case.parameters
        form = self.create_form()
        if p.get("published"):
            self.question(form)
            self.publish(form)
        query = {"_id": ObjectId(form["form_id"])}
        before = self.e.db.Question_forms.find_one(query)["revision"]
        initial_count = int(p.get("published", False))
        data = self.call(
            "POST", f"/surveys/{form['form_id']}/questions", p["body"], role=p.get("role", "owner"),
            code=p["code"], message=p.get("message"),
        )
        self.count("Questions", initial_count + int(p["code"] == 0))
        if p["code"]:
            self.stored("Question_forms", query, "revision", before)
        else:
            self.t.check("题型", data["type"], p["body"]["type"])
            self.t.check("题目顺序", data["order"], initial_count + 1)
            self.t.check("默认非必答", data["validation"]["required"], False)
            if data["type"] in ("single", "multiple"):
                self.t.check("选项数量", len(data["options"]), len(p["body"]["options"]))
                self.t.check("新选项 ID 有效", all(ObjectId.is_valid(o["option_id"]) for o in data["options"]), True)
            else:
                self.t.check("填空题没有选项", data["options"], [])
            self.stored("Questions", {"_id": ObjectId(data["question_id"])}, "form_id", query["_id"])

    def prepare_jump(self, kind):
        form = self.create_form()
        first = self.question(form, kind, validation={"required": True})
        second = self.question(form, validation={"required": True})
        third = self.question(form, validation={"required": True})
        if kind == "number":
            rules = [
                {"condition": {"op": "lt", "value": 5}, "target": third["question_id"]},
                {"condition": {"op": "gte", "value": 5}, "target": "end"},
            ]
        else:
            value = self.answer(first, "A" if kind == "single" else ["A", "B"])["value"]
            rules = [{"condition": {"op": "eq" if kind == "single" else "exact", "value": value},
                      "target": third["question_id"]}]
        self.set_rules(form, first, rules, stage="准备")
        self.publish(form)
        return form, first, second, third

    def test_jump(self, case):
        p = case.parameters
        form, first, second, third = self.prepare_jump(p["kind"])
        result = self.fill(form, [self.answer(first, p["value"])])
        expected = {"q2": second["question_id"], "q3": third["question_id"], "end": None}[p["destination"]]
        actual = result["next_question"]["question_id"] if result["next_question"] else None
        self.t.check("下一题", actual, expected)
        self.t.check("结束标记", result["complete"], expected is None)
        self.count("Responses", 0)

    def test_invalid_jump(self, case):
        mode = case.parameters["invalid"]
        form = self.create_form()
        first, second = self.question(form, "number"), self.question(form, "number")
        third = self.question(form)
        foreign = self.question(self.create_form())
        source = second if mode == "backward" else first
        target = {"self": first["question_id"], "backward": first["question_id"],
                  "foreign": foreign["question_id"], "missing": str(ObjectId()),
                  "overlap": third["question_id"]}[mode]
        rules = [{"condition": {"op": "eq", "value": 1}, "target": target}]
        if mode == "overlap":
            rules = [{"condition": {"op": "lte", "value": 5}, "target": target},
                     {"condition": {"op": "gte", "value": 5}, "target": "end"}]
        query = {"_id": ObjectId(form["form_id"])}
        before = self.e.db.Question_forms.find_one(query)["revision"]
        self.set_rules(form, source, rules, code=4001)
        self.stored("Questions", {"_id": ObjectId(source["question_id"])}, "jump_rules", [])
        self.stored("Question_forms", query, "revision", before)

    def test_skip_path(self, case):
        form, first, second, third = self.prepare_jump("single")
        answers = [self.answer(first, "B"), self.answer(second, "旧答案"), self.answer(third, "末题答案")]
        if case.parameters["change"]:
            initial = self.fill(form, answers)
            self.t.check("修改前经过三题", len(initial["answers"]), 3)
        answers[0] = self.answer(first, "A")
        result = self.fill(form, answers)
        self.t.check("清除跳过题目", result["discarded_question_ids"], [second["question_id"]])
        expected = [answers[0], answers[2]]
        self.t.check("实际路径答案", result["answers"], expected)
        self.fill(form, answers, request_id=case.id)
        self.count("Responses", 1)
        self.stored("Responses", {}, "answers", expected)

    def test_validation(self, case):
        p = case.parameters
        form = self.create_form()
        question = self.question(form, p["kind"], validation=p["limits"])
        self.publish(form)
        answers = [self.answer(question, p["value"])]
        progress = self.fill(form, answers, code=p["code"], message=p["message"])
        result = self.fill(form, answers, request_id=case.id, code=p["code"], message=p["message"])
        self.count("Responses", int(p["code"] == 0))
        if p["code"] == 0:
            self.t.check("完整路径已结束", progress["complete"], True)
            self.t.check("提交返回字段", sorted(result), ["response_id", "submitted_at"])
            stored_answers = self.e.db.Responses.find_one()["answers"]
            empty = p["value"] in (None, "") or p["value"] == []
            self.t.check("非空答案项数量", len(stored_answers), 0 if empty else 1, source="MongoDB find_one")

    def test_submission(self, case):
        p = case.parameters
        form = self.create_form(
            allow_anonymous=p["flag"] if p["mode"] == "normal" else False,
            allow_multiple_submissions=p["flag"] if p["mode"] != "normal" else False,
        )
        question = self.question(form, validation={"required": True})
        self.publish(form)
        answers = [self.answer(question, "第一份")]
        first = self.fill(form, answers, request_id="submit-1")
        count = 1
        if p["mode"] != "normal":
            key = "submit-2" if p["mode"] == "repeat" else "submit-1"
            if p["mode"] == "changed":
                answers = [self.answer(question, "第二份")]
            code = 4090 if p["mode"] == "changed" or (p["mode"] == "repeat" and not p["flag"]) else 0
            result = self.fill(form, answers, request_id=key, code=code)
            if p["mode"] == "idempotent":
                self.t.check("幂等响应完全相同", result, first)
            if p["mode"] == "repeat" and p["flag"]:
                count = 2
                self.t.check("再次填写生成不同提交 ID", result["response_id"] != first["response_id"], True)
        self.count("Responses", count)
        self.t.check("提交输出字段", sorted(first), ["response_id", "submitted_at"])
        self.stored("Responses", {"_id": ObjectId(first["response_id"])}, "answers",
                    [self.answer(question, "第一份")])
        self.stored("Responses", {"_id": ObjectId(first["response_id"])}, "is_anonymous",
                    p["flag"] if p["mode"] == "normal" else False)
        self.stored("Responses", {"_id": ObjectId(first["response_id"])}, "respondent_id",
                    self.e.db.Users.find_one({"username": "reader"})["_id"])

    def set_deadline(self, form):
        limit = self.e.clock.now + timedelta(hours=1)
        self.call("PUT", f"/surveys/{form['form_id']}/deadline",
                  {"deadline": limit.isoformat()}, stage="准备")
        return limit

    def move_clock(self, limit):
        self.t.record("control", action="推进注入业务时钟", before=self.e.clock.now, after=limit)
        self.e.clock.now = limit

    def test_closed_submission(self, case):
        p = case.parameters
        form = self.create_form()
        question = self.question(form, validation={"required": True})
        limit = self.set_deadline(form) if p["expired"] else None
        self.publish(form)
        answers = [self.answer(question, "第一份")]
        previous = self.fill(form, answers, request_id="closed-1") if p["retry"] else None
        if p["expired"]:
            self.move_clock(limit)
        else:
            self.call("POST", f"/surveys/{form['form_id']}/close")
        result = self.fill(form, answers, request_id="closed-1", code=0 if p["retry"] else 4090)
        self.count("Responses", 1 if p["retry"] else 0)
        if p["retry"]:
            self.t.check("关闭或截止后重试返回原结果", result, previous)

    def test_concurrent_submission(self, case):
        p = case.parameters
        form = self.create_form()
        question = self.question(form, validation={"required": True})
        limit = self.set_deadline(form) if p["mode"] == "expiry_race" else None
        self.publish(form)
        answers = [self.answer(question, "并发答案")]
        if p["mode"] in ("close_race", "expiry_race"):
            entered, release = Event(), Event()

            def controlled(*args, **kwargs):
                result = replay_answers(*args, **kwargs)
                self.t.record("control", action="提交已完成路径校验")
                if p["mode"] == "expiry_race":
                    self.move_clock(limit)
                else:
                    entered.set()
                    assert release.wait(15), "关闭并发控制超时"
                return result

            self.monkeypatch.setattr("app.filling_service.replay_answers", controlled)
            if p["mode"] == "expiry_race":
                self.fill(form, answers, request_id=case.id, code=4090)
            else:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.fill, form, answers, request_id=case.id, code=4090)
                    try:
                        self.t.check("到达暂停点", entered.wait(15), True)
                        self.call("POST", f"/surveys/{form['form_id']}/close")
                    finally:
                        release.set()
                    future.result()
        else:
            roles = ["owner", "reader"] if p["mode"] == "people" else ["reader"] * 3

            def send(index):
                key = "parallel-same" if p["mode"] == "same_request" else f"parallel-{index}"
                # 竞争胜者不预先指定，先记录原始响应，再按允许的结果集合断言。
                if p["mode"] == "different_requests":
                    path = urlsplit(form["access_link"]).path + "/submit"
                    body = {"requestId": key, "answers": answers}
                    event = self.t.record("api", stage="执行", method="POST", path=path, role="reader", json=body)
                    response = self.e.client.post(path, headers=self.e.reader, json=body)
                    actual = response.json()
                    self.t.finish_request(event, http_status=response.status_code, response=actual)
                    self.t.check("竞争响应状态与业务码对应", response.status_code, HTTP_CODES[actual["code"]])
                    return actual
                result = self.fill(form, answers, request_id=key, role=roles[index])
                return {"code": 0, "data": result}

            with ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(send, range(len(roles))))
            self.t.check("并发结果业务码集合", sorted(r["code"] for r in results), p["codes"])
            if p["mode"] == "same_request":
                for result in results[1:]:
                    self.t.check("并发重试返回同一提交", result["data"], results[0]["data"])
        self.count("Responses", p["count"])

    @staticmethod
    def values(stats):
        return [entry["value"] for entry in stats["contents"]["items"]]

    def test_statistics(self, case):
        getattr(self, "statistics_" + case.parameters["mode"])(case)

    def statistics_totals(self, case):
        form = self.create_form(allow_multiple_submissions=True)
        questions = [self.question(form, kind) for kind in ("single", "multiple", "text", "number")]
        self.publish(form)
        data = [["A", ["A", "B"], "重复内容", 0], ["A", ["B"], "重复内容", 10], ["B", [], "", None]]
        for index, row in enumerate(data):
            answers = [self.answer(q, value) for q, value in zip(questions, row)]
            self.fill(form, answers, request_id=f"stats-{index}", stage="准备")
            if index == 0:
                self.fill(form, answers, request_id="stats-0", stage="准备")
        result = self.stats(form)
        self.t.check("整卷提交份数", result["submission_count"], 3)
        one, many, text, number = result["questions"]
        self.t.check("各题有效回答数", [q["answer_count"] for q in result["questions"]], [3, 2, 2, 2])
        self.t.check("单选按配置顺序计数", [o["count"] for o in one["options"]], [2, 1, 0])
        self.t.check("多选选项计数", [o["count"] for o in many["options"]], [1, 2, 0])
        self.t.check("文本重复内容保留", self.values(text), ["重复内容", "重复内容"])
        self.t.check("数字原值", self.values(number), [0, 10])
        self.t.check("数字平均值", number["average"], 5)
        for q, expected in zip(questions, result["questions"]):
            self.t.check("单题与整卷一致", self.stats(form, q)["question"], expected)
        self.count("Responses", 3)

    def statistics_empty(self, case):
        form = self.create_form()
        questions = [self.question(form, kind) for kind in ("single", "multiple", "text", "number")]
        result = self.stats(form)
        self.t.check("无提交时总数", result["submission_count"], 0)
        for q, stats in zip(questions, result["questions"]):
            self.t.check("空问卷题目回答数", stats["answer_count"], 0)
            if "options" in stats:
                self.t.check("全部选项零计数", [o["count"] for o in stats["options"]], [0, 0, 0])
            else:
                self.t.check("空内容列表", self.values(stats), [])
            self.t.check("空问卷单题统计一致", self.stats(form, q)["question"], stats)
        self.t.check("空平均值不能为 0", result["questions"][-1]["average"], None)

    def statistics_pagination(self, case):
        kind = case.parameters["kind"]
        form = self.create_form(allow_multiple_submissions=True)
        question = self.question(form, kind)
        self.publish(form)
        expected = list(range(27)) if kind == "number" else [f"内容{i}" for i in range(27)]
        # 较晚组使用更小的 ID，组内递增；再逆序插入，分别检验主、次排序键。
        documents = [
            {"_id": ObjectId(f"{(9 - i // 3) * 100 + i % 3:024x}"), "form_id": ObjectId(form["form_id"]),
             "respondent_id": self.e.db.Users.find_one({"username": "reader"})["_id"],
             "submitted_at": self.e.clock.now + timedelta(seconds=i // 3),
             "answers": [self.answer(question, value)]}
            for i, value in enumerate(expected)
        ]
        self.t.record("database_setup", action="逆序插入旧格式答卷，仅用于排序专项",
                      collection="Responses", documents=documents[::-1])
        self.e.db.Responses.insert_many(documents[::-1])
        self.count("Responses", 27)
        first = self.stats(form)["questions"][0]
        self.t.check("整卷返回前 20 条", self.values(first), expected[:20])
        for page in (1, 2, 3, 4):
            stats = self.stats(form, question, params={"page": page, "page_size": 10})["question"]
            self.t.check(f"第 {page} 页内容", self.values(stats), expected[(page - 1) * 10:page * 10])
            self.t.check(f"第 {page} 页完整总数", stats["contents"]["total"], 27)
            if kind == "number":
                self.t.check(f"第 {page} 页平均值基于全部 27 条", stats["average"], 13)

    def statistics_privacy(self, case):
        form = self.create_form(allow_anonymous=case.parameters["anonymous"])
        question = self.question(form)
        self.publish(form)
        self.fill(form, [self.answer(question, "测试内容")], request_id=case.id, stage="准备")
        forbidden = {"respondent_id", "username", "user_id", "owner_id", "request_id",
                     "request_hash", "response_id", "submitted_at", "_id", "password_hash", "token_hash"}

        def keys(value):
            if isinstance(value, dict):
                return set(value).union(*(keys(child) for child in value.values()))
            if isinstance(value, list):
                return set().union(*(keys(child) for child in value))
            return set()

        for question_arg in (None, question):
            self.stats(form, question_arg, role=None, code=4010)
            self.stats(form, question_arg, role="reader", code=4030)
            result = self.stats(form, question_arg)
            self.t.check("统计中不存在禁止的身份字段", sorted(keys(result) & forbidden), [])
            stats = result["question"] if question_arg else result["questions"][0]
            self.t.check("内容项只有 value", stats["contents"]["items"], [{"value": "测试内容"}])

    def statistics_snapshot(self, case):
        form = self.create_form(allow_multiple_submissions=True)
        question = self.question(form, "number")
        self.publish(form)
        self.fill(form, [self.answer(question, 10)], request_id="snapshot-1", stage="准备")
        entered, release = Event(), Event()

        def pause_once():
            if not entered.is_set():
                self.t.record("control", action="统计已完成前段读取，暂停后续查询")
                entered.set()
                assert release.wait(15), "快照测试同步超时"

        if case.parameters["scope"] == "whole":
            original = StatisticsService.submission_count

            def controlled(service, *args, **kwargs):
                result = original(service, *args, **kwargs)
                pause_once()
                return result

            self.monkeypatch.setattr(StatisticsService, "submission_count", controlled)
            target = None
        else:
            def controlled(*args, **kwargs):
                result = content_summary(*args, **kwargs)
                pause_once()
                return result

            self.monkeypatch.setattr("app.statistics_pipeline.content_summary", controlled)
            target = question
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.stats, form, target)
            try:
                self.t.check("统计已到达暂停点", entered.wait(15), True)
                self.fill(form, [self.answer(question, 20)], request_id="snapshot-2")
                self.count("Responses", 2)
            finally:
                release.set()
            old = future.result()
        for label, result, count, expected_values, average in (
            ("当前快照", old, 1, [10], 10),
            ("后续请求", self.stats(form, target), 2, [10, 20], 15),
        ):
            stats = result["question"] if target else result["questions"][0]
            self.t.check(label + " 总份数", result["submission_count"], count)
            self.t.check(label + " 题目回答数", stats["answer_count"], count)
            self.t.check(label + " 内容列表", self.values(stats), expected_values)
            self.t.check(label + " 平均值", stats["average"], average)
