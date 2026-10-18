from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from sys import float_info
from threading import Event
from uuid import uuid4

import pytest
from bson import ObjectId

from app.statistics_pipeline import content_summary
from app.statistics_service import StatisticsService
from test_filling import item, setup_form, submit
from test_surveys import add, create, deadline, error, ok, patch, publish


def whole(env, form, headers=None):
    return env.client.get(
        f"/surveys/{form['form_id']}/statistics",
        headers=env.owner if headers is None else headers,
    )


def single(env, form, question, headers=None, **params):
    return env.client.get(
        f"/surveys/{form['form_id']}/questions/{question['question_id']}/statistics",
        headers=env.owner if headers is None else headers, params=params,
    )


def choices(question, *positions):
    return [question["options"][index]["option_id"] for index in positions]


def seed(env, form, answers, index=0):
    return {
        "_id": ObjectId(f"{index + 1:024x}"),
        "form_id": ObjectId(form["form_id"]),
        "respondent_id": ObjectId(),
        "submitted_at": env.clock.now + timedelta(seconds=index // 3),
        "answers": answers,
    }


def values(question_statistics):
    return [entry["value"] for entry in question_statistics["contents"]["items"]]


def test_empty_draft_returns_zero_statistics_and_no_average(survey_env):
    e = survey_env
    form = create(e)
    assert ok(whole(e, form))["questions"] == []
    questions = [ok(add(e, form, kind)) for kind in ("single", "multiple", "text", "number")]
    result = ok(whole(e, form))
    assert result["submission_count"] == 0 and result["status"] == "draft"
    assert [q["question_id"] for q in result["questions"]] == [q["question_id"] for q in questions]
    for q, stats in zip(questions, result["questions"]):
        assert stats["answer_count"] == 0
        assert ok(single(e, form, q))["question"] == stats
        if "options" in stats:
            assert [option["count"] for option in stats["options"]] == [0, 0, 0]
        else:
            assert stats["contents"] == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert result["questions"][-1]["average"] is None


def test_all_types_count_submissions_not_distinct_users(survey_env):
    e = survey_env
    form = create(e, allow_multiple_submissions=True)
    one, many, text, number = [ok(add(e, form, kind)) for kind in ("single", "multiple", "text", "number")]
    ok(publish(e, form))
    first = [
        item(one, choices(one, 0)[0]), item(many, choices(many, 0, 1)),
        item(text, "重复内容"), item(number, 0),
    ]
    key = str(uuid4())
    ok(submit(e, form, first, key))
    ok(submit(e, form, first, key))
    ok(submit(e, form, [
        item(one, choices(one, 0)[0]), item(many, choices(many, 1)),
        item(text, "重复内容"), item(number, 10),
    ]))
    ok(submit(e, form, [
        item(one, choices(one, 1)[0]), item(many, None),
        item(text, " \t "), item(number, None),
    ]))
    result = ok(whole(e, form))
    assert result["submission_count"] == 3
    one_stats, many_stats, text_stats, number_stats = result["questions"]
    assert one_stats["answer_count"] == 3
    assert [o["count"] for o in one_stats["options"]] == [2, 1, 0]
    assert many_stats["answer_count"] == 2
    assert [o["count"] for o in many_stats["options"]] == [1, 2, 0]
    assert sum(o["count"] for o in many_stats["options"]) > many_stats["answer_count"]
    assert text_stats["answer_count"] == 2 and values(text_stats) == ["重复内容", "重复内容"]
    assert number_stats["answer_count"] == 2 and values(number_stats) == [0, 10]
    assert number_stats["average"] == 5
    for question, stats in zip((one, many, text, number), result["questions"]):
        individual = ok(single(e, form, question))
        assert individual["submission_count"] == 3 and individual["question"] == stats


def test_skipped_required_questions_do_not_enter_counts_or_average(survey_env):
    e = survey_env
    form = create(e, allow_multiple_submissions=True)
    first = ok(add(e, form, "single", validation={"required": True}))
    skipped = ok(add(e, form, "number", validation={"required": True}))
    ok(patch(e, form, first, jump_rules=[
        {"condition": {"op": "eq", "value": choices(first, 0)[0]}, "target": "end"}
    ]))
    ok(publish(e, form))
    ok(submit(e, form, [item(first, choices(first, 0)[0]), item(skipped, 999)]))
    ok(submit(e, form, [item(first, choices(first, 1)[0]), item(skipped, 4)]))
    result = ok(whole(e, form))
    assert result["submission_count"] == 2
    assert result["questions"][1]["answer_count"] == 1
    assert result["questions"][1]["average"] == 4
    assert values(result["questions"][1]) == [4]


def test_blank_submission_counts_for_form_but_not_question(survey_env):
    e = survey_env
    form, q = setup_form(e)
    ok(submit(e, form, []))
    result = ok(whole(e, form))
    assert result["submission_count"] == 1
    assert result["questions"][0]["answer_count"] == 0
    assert values(result["questions"][0]) == []


@pytest.mark.parametrize("kind", ["text", "number"])
def test_stable_pagination_uses_time_then_id_and_averages_all_rows(survey_env, kind):
    e = survey_env
    form, q = setup_form(e, multiple=True, kind=kind)
    expected = list(range(27)) if kind == "number" else [f"内容{i}" for i in range(27)]
    documents = [seed(e, form, [item(q, value)], i) for i, value in enumerate(expected)]
    e.db.Responses.insert_many(documents[::-1])
    initial = ok(whole(e, form))["questions"][0]
    assert values(initial) == expected[:20]
    assert initial["contents"]["total"] == 27
    if kind == "number":
        assert initial["average"] == 13
    for page in (1, 2, 3, 4):
        stats = ok(single(e, form, q, page=page, page_size=10))["question"]
        assert values(stats) == expected[(page - 1) * 10:page * 10]
        assert stats["answer_count"] == stats["contents"]["total"] == 27
        assert stats["contents"]["page"] == page and stats["contents"]["page_size"] == 10
        if kind == "number":
            assert stats["average"] == 13
    e.clock.now += timedelta(hours=1)
    ok(submit(e, form, [item(q, 27 if kind == "number" else "追加")]))
    assert values(ok(single(e, form, q, page=1, page_size=10))["question"]) == expected[:10]


def test_content_is_preserved_without_deduplicating_or_trimming(survey_env):
    e = survey_env
    form, q = setup_form(e, multiple=True)
    expected = [" 中文 ", "$value", "重复", "重复", "<script>只是文本</script>"]
    for value in expected:
        ok(submit(e, form, [item(q, value)]))
    assert values(ok(single(e, form, q))["question"]) == expected


@pytest.mark.parametrize("anonymous", [True, False])
def test_statistics_do_not_expose_identity_or_internal_response_metadata(survey_env, anonymous):
    e = survey_env
    form, q = setup_form(e, anonymous=anonymous)
    ok(submit(e, form, [item(q, "内容")]))
    # 历史记录即使缺少匿名标记，也不能导致统计结果泄露身份。
    e.db.Responses.update_many({}, {"$unset": {"is_anonymous": ""}})
    forbidden = {
        "respondent_id", "username", "user_id", "owner_id", "request_id", "request_hash",
        "response_id", "submitted_at", "_id", "token_hash", "password_hash",
    }

    def check(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(ok(whole(e, form)))
    stats = ok(single(e, form, q))
    check(stats)
    assert stats["question"]["contents"]["items"] == [{"value": "内容"}]


@pytest.mark.parametrize("state", ["draft", "published", "closed", "expired"])
def test_statistics_are_available_in_every_state(survey_env, state):
    e = survey_env
    form = create(e)
    q = ok(add(e, form, "number"))
    if state == "expired":
        ok(deadline(e, form, (e.clock.now + timedelta(hours=1)).isoformat()))
    if state != "draft":
        ok(publish(e, form))
        ok(submit(e, form, [item(q, 2)]))
    if state == "closed":
        ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
    if state == "expired":
        e.clock.now += timedelta(hours=1)
    result = ok(whole(e, form))
    assert result["status"] == ("closed" if state == "expired" else state)
    assert result["submission_count"] == (0 if state == "draft" else 1)
    assert ok(single(e, form, q))["question"] == result["questions"][0]
    if state == "expired":
        assert e.db.Question_forms.find_one()["status"] == "published"


def test_auth_ownership_and_foreign_question_scope(survey_env):
    e = survey_env
    form, q = setup_form(e)
    other, other_q = setup_form(e)
    for query in (lambda headers: whole(e, form, headers), lambda headers: single(e, form, q, headers)):
        error(query({}), 4010)
        error(query(e.reader), 4030, "无权限")
    error(single(e, form, other_q), 4040, "题目不存在")
    error(whole(e, {"form_id": str(ObjectId())}), 4040)
    error(single(e, form, {"question_id": str(ObjectId())}), 4040)
    error(whole(e, {"form_id": "bad-id"}), 4001)
    error(single(e, form, {"question_id": "bad-id"}), 4001)
    ok(submit(e, other, [item(other_q, "另一份问卷")]))
    assert ok(whole(e, form))["submission_count"] == 0


@pytest.mark.parametrize("params", [
    {"page": 0}, {"page": -1}, {"page": "text"}, {"page": 10**30},
    {"page_size": 0}, {"page_size": 101}, {"page_size": "bad"},
])
def test_invalid_pagination_is_parameter_error(survey_env, params):
    form, q = setup_form(survey_env)
    error(single(survey_env, form, q, **params), 4001)


def test_choice_option_order_is_configuration_order(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form, "single", options=[{"text": "Z"}, {"text": "A"}]))
    ok(publish(e, form))
    ok(submit(e, form, [item(q, choices(q, 1)[0])]))
    stats = ok(single(e, form, q, page=2, page_size=1))["question"]
    assert [o["text"] for o in stats["options"]] == ["Z", "A"]
    assert [o["count"] for o in stats["options"]] == [0, 1]
    assert "contents" not in stats


def test_legacy_records_without_submission_flags_are_included(survey_env):
    e = survey_env
    form, q = setup_form(e, kind="number")
    e.db.Responses.insert_many([seed(e, form, [item(q, n)], i) for i, n in enumerate([0, 4, 8])])
    result = ok(whole(e, form))
    assert result["submission_count"] == 3
    assert result["questions"][0]["average"] == 4
    assert values(result["questions"][0]) == [0, 4, 8]


def test_legacy_empty_or_wrong_type_values_do_not_inflate_numeric_denominator(survey_env):
    e = survey_env
    form, q = setup_form(e, kind="number")
    raw = [None, "", "12", True, [], float("nan"), float("inf"), float("-inf"), 0, 10]
    e.db.Responses.insert_many([seed(e, form, [item(q, value)], i) for i, value in enumerate(raw)])
    result = ok(single(e, form, q))
    assert result["submission_count"] == len(raw)
    assert result["question"]["answer_count"] == 2
    assert result["question"]["average"] == 5
    assert values(result["question"]) == [0, 10]


@pytest.mark.parametrize("kind", ["single", "multiple", "text"])
def test_legacy_empty_and_wrong_type_values_are_excluded(survey_env, kind):
    e = survey_env
    form, q = setup_form(e, kind=kind)
    raw = [None, "", " \t ", [], 123, True, {"unexpected": "value"}]
    if kind == "single":
        valid = choices(q, 0)[0]
        raw.append("nonexistent-option")
    elif kind == "multiple":
        valid = choices(q, 0, 1)
        raw.extend([choices(q, 0, 0), ["nonexistent-option"]])
    else:
        valid = " 有效内容 "
    raw.append(valid)
    e.db.Responses.insert_many([seed(e, form, [item(q, value)], i) for i, value in enumerate(raw)])
    stats = ok(single(e, form, q))["question"]
    assert stats["answer_count"] == 1
    if kind == "text":
        assert values(stats) == [valid]
    else:
        assert [o["count"] for o in stats["options"]] == ([1, 0, 0] if kind == "single" else [1, 1, 0])


@pytest.mark.parametrize("numbers,expected", [
    ([1e308, 1e308], 1e308),
    ([float_info.max, float_info.max], float_info.max),
    ([-float_info.max, float_info.max], 0),
    ([0.1, 0.2], 0.15),
    ([-2, 0, 5], 1),
])
def test_numeric_average_handles_valid_extreme_values(survey_env, numbers, expected):
    e = survey_env
    form, q = setup_form(e, multiple=True, kind="number")
    for value in numbers:
        ok(submit(e, form, [item(q, value)]))
    stats = ok(single(e, form, q))["question"]
    assert stats["answer_count"] == len(numbers)
    assert stats["average"] == pytest.approx(expected)


def test_statistics_do_not_mutate_business_data_or_create_caches(survey_env):
    e = survey_env
    form, q = setup_form(e)
    ok(submit(e, form, [item(q, "内容")]))
    collections = e.db.list_collection_names()
    before = {name: list(e.db[name].find()) for name in ("Questions", "Question_forms", "Responses")}
    e.clock.now += timedelta(hours=1)
    ok(whole(e, form))
    ok(single(e, form, q))
    assert set(e.db.list_collection_names()) == set(collections)
    assert {name: list(e.db[name].find()) for name in before} == before
    owner_id = e.db.Users.find_one({"username": "owner"})["_id"]
    assert e.db.Sessions.find_one({"user_id": owner_id})["expires_at"] == e.clock.now + timedelta(days=3)
    assert e.db.Responses.index_information()["form_question_oldest"]["key"] == [
        ("form_id", 1), ("answers.question_id", 1), ("submitted_at", 1), ("_id", 1),
    ]


@pytest.mark.parametrize("pause_at", ["total", "first_question"])
def test_whole_response_uses_one_snapshot_despite_concurrent_submission(survey_env, monkeypatch, pause_at):
    e = survey_env
    form = create(e, allow_multiple_submissions=True)
    one, number = ok(add(e, form, "single")), ok(add(e, form, "number"))
    ok(publish(e, form))
    ok(submit(e, form, [item(one, choices(one, 0)[0]), item(number, 10)]))
    entered, release = Event(), Event()
    method_name = "submission_count" if pause_at == "total" else "summarize_question"
    original = getattr(StatisticsService, method_name)

    def pause(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if not entered.is_set():
            entered.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr(StatisticsService, method_name, pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(whole, e, form)
        assert entered.wait(5)
        try:
            ok(submit(e, form, [item(one, choices(one, 1)[0]), item(number, 20)]))
            assert e.db.Responses.count_documents({}) == 2
        finally:
            release.set()
        result = ok(future.result())
    assert result["submission_count"] == 1
    assert [o["count"] for o in result["questions"][0]["options"]] == [1, 0, 0]
    assert result["questions"][1]["average"] == 10
    assert values(result["questions"][1]) == [10]
    latest = ok(whole(e, form))
    assert latest["submission_count"] == 2
    assert latest["questions"][1]["average"] == 15
    assert values(latest["questions"][1]) == [10, 20]


def test_single_question_summary_and_items_share_snapshot(survey_env, monkeypatch):
    e = survey_env
    form, q = setup_form(e, multiple=True, kind="number")
    ok(submit(e, form, [item(q, 10)]))
    entered, release = Event(), Event()

    def pause(*args, **kwargs):
        result = content_summary(*args, **kwargs)
        if not entered.is_set():
            entered.set()
            assert release.wait(10)
        return result

    monkeypatch.setattr("app.statistics_pipeline.content_summary", pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(single, e, form, q)
        assert entered.wait(5)
        try:
            ok(submit(e, form, [item(q, 20)]))
        finally:
            release.set()
        result = ok(future.result())
    assert result["submission_count"] == result["question"]["answer_count"] == 1
    assert result["question"]["contents"]["total"] == 1
    assert values(result["question"]) == [10]
    assert result["question"]["average"] == 10
    latest = ok(single(e, form, q))
    assert latest["question"]["average"] == 15 and values(latest["question"]) == [10, 20]
