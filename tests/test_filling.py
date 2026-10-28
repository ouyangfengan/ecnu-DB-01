from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.answer_engine import replay_answers
from app.database import create_indexes
from test_surveys import add, create, deadline, error, ok, patch, publish


def item(question, value):
    return {"question_id": question["question_id"], "value": value}


def setup_form(env, multiple=False, anonymous=False, kind="text", **limits):
    form = create(env, allow_multiple_submissions=multiple, allow_anonymous=anonymous)
    question = ok(add(env, form, kind, validation=limits))
    ok(publish(env, form))
    return form, question


def progress(env, form, answers=None, headers=None):
    return env.client.post(
        urlsplit(form["access_link"]).path + "/progress",
        headers=env.reader if headers is None else headers,
        json={"answers": [] if answers is None else answers},
    )


def submit(env, form, answers, request_id=None, headers=None):
    return env.client.post(
        urlsplit(form["access_link"]).path + "/submit",
        headers=env.reader if headers is None else headers,
        json={"requestId": request_id or str(uuid4()), "answers": answers},
    )


def responses(env, form, page=1, page_size=20, headers=None):
    return env.client.get(
        f"/surveys/{form['form_id']}/responses?page={page}&page_size={page_size}",
        headers=env.owner if headers is None else headers,
    )


@pytest.mark.parametrize("multiple", [False, True])
def test_same_request_retries_return_identical_success(survey_env, multiple):
    e = survey_env
    form, q = setup_form(e, multiple, required=True)
    e.clock.now += timedelta(microseconds=123456)
    answers, key = [item(q, "已提交")], str(uuid4())
    first = ok(submit(e, form, answers, key))
    original = e.db.Responses.find_one()
    revision = e.db.Question_forms.find_one()["revision"]
    e.clock.now += timedelta(hours=1)
    assert ok(submit(e, form, answers, key)) == first
    assert e.db.Responses.find_one() == original
    assert e.db.Question_forms.find_one()["revision"] == revision
    assert e.db.Responses.count_documents({}) == 1
    assert set(first) == {"response_id", "submitted_at"}
    assert original["answers"] == answers
    assert original["single_submission"] is (not multiple)
    assert original["request_id"] == key
    assert len(original["request_hash"]) == 64


@pytest.mark.parametrize("multiple", [False, True])
def test_same_key_changed_content_is_conflict(survey_env, multiple):
    e = survey_env
    form, q = setup_form(e, multiple)
    key = str(uuid4())
    ok(submit(e, form, [item(q, "第一次内容")], key))
    error(submit(e, form, [item(q, "更改内容")], key), 4090, "请求标识已用于其他提交内容")
    assert e.db.Responses.count_documents({}) == 1
    assert e.db.Responses.find_one()["answers"] == [item(q, "第一次内容")]


@pytest.mark.parametrize("multiple", [False, True])
def test_new_key_is_new_submission_only_when_allowed(survey_env, multiple):
    e = survey_env
    form, q = setup_form(e, multiple)
    first = ok(submit(e, form, [item(q, "答案")]))
    second = submit(e, form, [item(q, "答案")])
    if multiple:
        assert ok(second)["response_id"] != first["response_id"]
        assert e.db.Responses.count_documents({}) == 2
    else:
        error(second, 4090, "该问卷不允许重复提交")
        assert e.db.Responses.count_documents({}) == 1


@pytest.mark.parametrize("multiple", [False, True])
@pytest.mark.parametrize("closure", ["manual", "deadline"])
def test_retry_after_close_or_expiry_still_returns_original(survey_env, multiple, closure):
    e = survey_env
    form = create(e, allow_multiple_submissions=multiple)
    q = ok(add(e, form, validation={"required": True}))
    end = e.clock.now + timedelta(hours=1)
    ok(deadline(e, form, end.isoformat()))
    ok(publish(e, form))
    answers, key = [item(q, "答案")], str(uuid4())
    first = ok(submit(e, form, answers, key))
    if closure == "manual":
        ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
    else:
        e.clock.now = end
    assert ok(submit(e, form, answers, key)) == first
    error(submit(e, form, answers), 4090)
    error(submit(e, form, [item(q, "不同内容")], key), 4090, "请求标识已用于其他提交内容")
    assert e.db.Responses.count_documents({}) == 1


@pytest.mark.parametrize("anonymous", [False, True])
def test_anonymity_is_taken_from_form_and_identity_not_returned(survey_env, anonymous):
    e = survey_env
    form, q = setup_form(e, anonymous=anonymous)
    result = ok(submit(e, form, [item(q, "答案")]))
    document = e.db.Responses.find_one()
    assert document["is_anonymous"] is anonymous
    assert document["respondent_id"] == e.db.Users.find_one({"username": "reader"})["_id"]
    assert set(result) == {"response_id", "submitted_at"}
    for field, value in [
        ("is_anonymous", not anonymous), ("respondent_id", str(ObjectId())),
        ("allow_multiple_submissions", True), ("form_id", str(ObjectId())),
    ]:
        response = e.client.post(
            urlsplit(form["access_link"]).path + "/submit", headers=e.reader,
            json={"requestId": str(uuid4()), "answers": [item(q, "答案")], field: value},
        )
        error(response, 4001)


def test_response_detail_real_name_shows_identity_in_submission_order(survey_env):
    e = survey_env
    form, q = setup_form(e, multiple=True)
    first = ok(submit(e, form, [item(q, "第一次")]))
    e.clock.now += timedelta(seconds=1)
    second = ok(submit(e, form, [item(q, "第二次")]))
    e.clock.now += timedelta(seconds=1)
    third = ok(submit(e, form, [item(q, "第三次")], headers=e.owner))
    data = ok(responses(e, form, page_size=2))
    assert data["allow_anonymous"] is False and data["total"] == 3
    assert data["page"] == 1 and data["page_size"] == 2 and data["form_id"] == form["form_id"]
    assert [row["response_id"] for row in data["items"]] == [
        first["response_id"], second["response_id"],
    ]
    row = data["items"][0]
    assert set(row) == {
        "response_id", "submitted_at", "is_anonymous", "answers",
        "respondent_id", "respondent_username",
    }
    assert "request_id" not in row and "request_hash" not in row
    assert row["is_anonymous"] is False
    assert row["respondent_username"] == "reader"
    assert row["respondent_id"] == str(e.db.Users.find_one({"username": "reader"})["_id"])
    assert row["answers"] == [item(q, "第一次")]
    second_page = ok(responses(e, form, page=2, page_size=2))
    assert [row["response_id"] for row in second_page["items"]] == [third["response_id"]]
    assert second_page["items"][0]["respondent_username"] == "owner"


def test_response_detail_anonymous_hides_identity_but_keeps_record(survey_env):
    e = survey_env
    form, q = setup_form(e, anonymous=True)
    ok(submit(e, form, [item(q, "匿名答案")]))
    data = ok(responses(e, form))
    assert data["allow_anonymous"] is True and data["total"] == 1
    row = data["items"][0]
    assert set(row) == {"response_id", "submitted_at", "is_anonymous", "answers"}
    assert row["is_anonymous"] is True and row["answers"] == [item(q, "匿名答案")]
    assert "respondent_id" not in row and "respondent_username" not in row
    assert e.db.Responses.find_one()["respondent_id"] == (
        e.db.Users.find_one({"username": "reader"})["_id"]
    )


@pytest.mark.parametrize("anonymous", [False, True])
def test_response_detail_legacy_without_flag_falls_back_to_form_setting(survey_env, anonymous):
    e = survey_env
    form, q = setup_form(e, anonymous=anonymous)
    ok(submit(e, form, [item(q, "新答案")]))
    e.db.Responses.insert_one({
        "form_id": ObjectId(form["form_id"]),
        "respondent_id": e.db.Users.find_one({"username": "owner"})["_id"],
        "submitted_at": e.clock.now - timedelta(hours=1), "answers": [item(q, "历史答案")],
    })
    rows = ok(responses(e, form))["items"]
    legacy = rows[0]
    assert legacy["answers"] == [item(q, "历史答案")]
    assert legacy["is_anonymous"] is anonymous
    assert ("respondent_id" in legacy) is (not anonymous)
    if not anonymous:
        assert legacy["respondent_username"] == "owner"


def test_response_detail_is_owner_only_and_validates_ids(survey_env):
    e = survey_env
    form, _ = setup_form(e)
    assert ok(responses(e, form))["items"] == []
    error(responses(e, form, headers=e.reader), 4030, "无权限")
    error(e.client.get("/surveys/not-an-id/responses", headers=e.owner), 4001, "ID 格式无效")
    error(e.client.get(f"/surveys/{ObjectId()}/responses", headers=e.owner), 4040, "问卷不存在")
    error(e.client.get(f"/surveys/{form['form_id']}/responses"), 4010)


def test_progress_does_not_save_draft_and_returns_next_question(survey_env):
    e = survey_env
    form = create(e)
    first = ok(add(e, form, validation={"required": True}))
    second = ok(add(e, form))
    ok(publish(e, form))
    original = e.db.Question_forms.find_one()
    result = ok(progress(e, form))
    assert result["next_question"]["question_id"] == first["question_id"]
    assert result["answers"] == [] and not result["complete"]
    result = ok(progress(e, form, [item(first, "答案")]))
    assert result["next_question"]["question_id"] == second["question_id"]
    result = ok(progress(e, form, [item(first, "答案"), item(second, None)]))
    assert result["complete"] and result["next_question"] is None
    assert e.db.Responses.count_documents({}) == 0
    assert e.db.Question_forms.find_one() == original


def test_backtracking_discards_skipped_required_answers_and_submission_saves_only_path(survey_env):
    e = survey_env
    form = create(e)
    first = ok(add(e, form, "single", validation={"required": True}))
    second = ok(add(e, form, validation={"required": True}))
    third = ok(add(e, form, validation={"required": True}))
    selected = first["options"][0]["option_id"]
    ok(patch(e, form, first, jump_rules=[
        {"condition": {"op": "eq", "value": selected}, "target": third["question_id"]}
    ]))
    ok(publish(e, form))
    before = [
        item(first, first["options"][1]["option_id"]), item(second, "旧答案"), item(third, "末题"),
    ]
    assert len(ok(progress(e, form, before))["answers"]) == 3
    after = [item(first, selected), item(second, {"invalid": "不校验跳过题"}), item(third, "末题")]
    result = ok(progress(e, form, after))
    assert result["answers"] == [item(first, selected), item(third, "末题")]
    assert result["discarded_question_ids"] == [second["question_id"]]
    ok(submit(e, form, after))
    assert e.db.Responses.find_one()["answers"] == result["answers"]


def test_submit_recomputes_path_and_cannot_omit_required_answers(survey_env):
    e = survey_env
    form = create(e)
    first = ok(add(e, form, "single", validation={"required": True}))
    second = ok(add(e, form, validation={"required": True}))
    ok(patch(e, form, first, jump_rules=[{
        "condition": {"op": "eq", "value": first["options"][0]["option_id"]}, "target": "end",
    }]))
    ok(publish(e, form))
    error(submit(e, form, [item(first, first["options"][1]["option_id"])]), 4001, "第 2 题：该题为必答题")
    assert e.db.Responses.count_documents({}) == 0
    ok(submit(e, form, [item(first, first["options"][0]["option_id"])]))
    assert len(e.db.Responses.find_one()["answers"]) == 1


def test_numeric_zero_is_saved_and_empty_optional_answers_are_not(survey_env):
    e = survey_env
    form = create(e)
    zero = ok(add(e, form, "number", validation={"required": True, "integer_only": True}))
    text = ok(add(e, form))
    multi = ok(add(e, form, "multiple", validation={"min_selected": 2}))
    ok(publish(e, form))
    ok(submit(e, form, [item(zero, 0), item(text, " \t "), item(multi, [])]))
    assert e.db.Responses.find_one()["answers"] == [item(zero, 0)]


def test_all_optional_form_can_be_submitted_without_answers(survey_env):
    e = survey_env
    form, _ = setup_form(e)
    ok(submit(e, form, []))
    assert e.db.Responses.find_one()["answers"] == []


@pytest.mark.parametrize("kind,value,limits", [
    ("multiple", [], {"required": True}),
    ("text", "", {"required": True}),
    ("text", "过长的内容", {"max_length": 2}),
    ("number", True, {}),
    ("number", "1", {}),
    ("number", 2.1, {"integer_only": True}),
    ("number", 11, {"max_value": 10}),
    ("single", "missing-option", {}),
])
def test_validation_failures_do_not_save_or_consume_request_id(survey_env, kind, value, limits):
    e = survey_env
    form, q = setup_form(e, kind=kind, **limits)
    key = str(uuid4())
    before = e.db.Question_forms.find_one()
    error(progress(e, form, [item(q, value)]), 4001)
    error(submit(e, form, [item(q, value)], key), 4001)
    assert e.db.Responses.count_documents({}) == 0
    assert e.db.Question_forms.find_one() == before
    valid = {
        "single": q["options"][0]["option_id"] if q["options"] else None,
        "multiple": [q["options"][0]["option_id"]] if q["options"] else None,
        "text": "好", "number": 1,
    }[kind]
    ok(submit(e, form, [item(q, valid)], key))


def test_request_hash_accepts_reordered_answers_and_choices(survey_env):
    e = survey_env
    form = create(e)
    one = ok(add(e, form, "multiple"))
    two = ok(add(e, form, "number"))
    ok(publish(e, form))
    choices = [o["option_id"] for o in one["options"]][:2]
    key = str(uuid4())
    first = ok(submit(e, form, [item(one, choices), item(two, 1.0)], key))
    assert ok(submit(e, form, [item(two, 1), item(one, choices[::-1])], key)) == first


@pytest.mark.parametrize("multiple", [False, True])
def test_concurrent_identical_retries_all_succeed_once(survey_env, multiple):
    e = survey_env
    form, q = setup_form(e, multiple)
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: submit(e, form, [item(q, "相同答案")], key), range(4)))
    records = [ok(response) for response in results]
    assert all(record == records[0] for record in records)
    assert e.db.Responses.count_documents({}) == 1


@pytest.mark.parametrize("multiple", [False, True])
def test_concurrent_new_requests_obey_submission_limit(survey_env, multiple):
    e = survey_env
    form, q = setup_form(e, multiple)
    keys = [str(uuid4()) for _ in range(3)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(lambda key: submit(e, form, [item(q, key)], key), keys))
    codes = sorted(response.json()["code"] for response in responses)
    assert codes == ([0, 0, 0] if multiple else [0, 4090, 4090])
    assert e.db.Responses.count_documents({}) == (3 if multiple else 1)
    for key, response in zip(keys, responses):
        if response.json()["code"] == 0:
            assert ok(submit(e, form, [item(q, key)], key)) == ok(response)


@pytest.mark.parametrize("multiple", [False, True])
def test_concurrent_same_key_different_content_has_one_winner(survey_env, multiple):
    e = survey_env
    form, q = setup_form(e, multiple)
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda text: submit(e, form, [item(q, text)], key), ["A", "B"]))
    assert sorted(response.json()["code"] for response in responses) == [0, 4090]
    assert e.db.Responses.count_documents({}) == 1
    winner = "A" if responses[0].json()["code"] == 0 else "B"
    assert e.db.Responses.find_one()["answers"] == [item(q, winner)]


def test_same_request_id_is_scoped_by_form_and_user(survey_env):
    e = survey_env
    form, q = setup_form(e)
    key = str(uuid4())
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda header: submit(e, form, [item(q, "答案")], key, headers=header),
            [e.reader, e.owner],
        ))
    assert len({ok(response)["response_id"] for response in results}) == 2
    other, other_q = setup_form(e)
    third = ok(submit(e, other, [item(other_q, "其他问卷")], key))
    assert third["response_id"] not in {ok(response)["response_id"] for response in results}
    assert e.db.Responses.count_documents({}) == 3


def test_close_wins_against_inflight_submission_without_partial_write(survey_env, monkeypatch):
    e = survey_env
    form, q = setup_form(e)
    entered, release = Event(), Event()

    def paused(*args, **kwargs):
        result = replay_answers(*args, **kwargs)
        entered.set()
        assert release.wait(10)
        return result

    monkeypatch.setattr("app.filling_service.replay_answers", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(submit, e, form, [item(q, "答案")])
        assert entered.wait(5)
        try:
            ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
        finally:
            release.set()
        error(future.result(), 4090, "问卷已关闭")
    assert e.db.Responses.count_documents({}) == 0


def test_expiry_during_submission_rolls_back_insert(survey_env, monkeypatch):
    e = survey_env
    form = create(e)
    q = ok(add(e, form))
    limit = e.clock.now + timedelta(hours=1)
    ok(deadline(e, form, limit.isoformat()))
    ok(publish(e, form))
    before = e.db.Question_forms.find_one()

    def expire_after_validation(*args, **kwargs):
        result = replay_answers(*args, **kwargs)
        e.clock.now = limit
        return result

    monkeypatch.setattr("app.filling_service.replay_answers", expire_after_validation)
    error(submit(e, form, [item(q, "答案")]), 4090, "问卷已截止")
    assert e.db.Responses.count_documents({}) == 0
    assert e.db.Question_forms.find_one() == before


def test_authentication_cannot_be_bypassed_by_existing_request_id(survey_env):
    e = survey_env
    form, q = setup_form(e)
    answers, key = [item(q, "答案")], str(uuid4())
    ok(submit(e, form, answers, key))
    for suffix in ("/progress", "/submit"):
        error(e.client.post(
            urlsplit(form["access_link"]).path + suffix,
            json={"answers": answers, **({"requestId": key} if suffix == "/submit" else {})},
        ), 4010)
    ok(e.client.post("/auth/logout", headers=e.reader))
    error(submit(e, form, answers, key), 4010)


def test_legacy_responses_remain_readable_and_enforce_single_limit(survey_env):
    e = survey_env
    form, q = setup_form(e)
    legacy = {
        "form_id": ObjectId(form["form_id"]),
        "respondent_id": e.db.Users.find_one({"username": "reader"})["_id"],
        "submitted_at": e.clock.now, "answers": [item(q, "历史答案")],
    }
    e.db.Responses.insert_one(legacy)
    create_indexes(e.db)
    error(submit(e, form, [item(q, "新答案")]), 4090, "该问卷不允许重复提交")
    assert e.db.Responses.count_documents({}) == 1
    assert "request_id" not in e.db.Responses.find_one()


def test_database_unique_indexes_enforce_both_constraints(survey_env):
    e = survey_env
    form, q = setup_form(e)
    ok(submit(e, form, [item(q, "答案")]))
    document = e.db.Responses.find_one()
    indexes = e.db.Responses.index_information()
    assert indexes["unique_submission_request"]["unique"]
    assert indexes["one_submission_per_user"]["unique"]
    for same_request in (True, False):
        clone = {**document, "_id": ObjectId()}
        if not same_request:
            clone["request_id"] = str(uuid4())
        with pytest.raises(DuplicateKeyError):
            e.db.Responses.insert_one(clone)


@pytest.mark.parametrize("key", ["", "x" * 129, "with space", None, 123])
def test_invalid_request_ids(survey_env, key):
    e = survey_env
    form, _ = setup_form(e)
    response = e.client.post(
        urlsplit(form["access_link"]).path + "/submit", headers=e.reader,
        json={"requestId": key, "answers": []},
    )
    error(response, 4001)
    assert e.db.Responses.count_documents({}) == 0


def test_missing_key_duplicate_question_foreign_question_and_nonfinite_json(survey_env):
    e = survey_env
    form, q = setup_form(e)
    path = urlsplit(form["access_link"]).path + "/submit"
    error(e.client.post(path, headers=e.reader, json={"answers": []}), 4001)
    error(submit(e, form, [item(q, "a"), item(q, "b")]), 4001)
    error(submit(e, form, [{"question_id": str(ObjectId()), "value": "外来答案"}]), 4001)
    error(submit(e, form, [{"question_id": "bad-id", "value": "答案"}]), 4001)
    response = e.client.post(
        path, headers={**e.reader, "Content-Type": "application/json"},
        content='{"requestId":"nan-test","answers":[{"question_id":"' + q["question_id"] + '","value":NaN}]}',
    )
    error(response, 4001)
    assert e.db.Responses.count_documents({}) == 0


def test_invalid_unicode_text_is_a_validation_error_not_server_error(survey_env):
    e = survey_env
    form, q = setup_form(e)
    path = urlsplit(form["access_link"]).path
    for suffix in ("/progress", "/submit"):
        payload = (
            '{"requestId":"unicode-test",' if suffix == "/submit" else "{"
        ) + '"answers":[{"question_id":"' + q["question_id"] + '","value":"\\ud800"}]}'
        response = e.client.post(
            path + suffix, headers={**e.reader, "Content-Type": "application/json"},
            content=payload,
        )
        error(response, 4001, "第 1 题：文本包含无效的 Unicode 字符")
    assert e.db.Responses.count_documents({}) == 0


def test_draft_unknown_link_and_already_submitted_progress(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form))
    error(progress(e, form), 4090, "问卷尚未发布")
    error(submit(e, form, [item(q, "答案")]), 4090, "问卷尚未发布")
    for suffix in ("/progress", "/submit"):
        payload = {"answers": [], **({"requestId": "unknown"} if suffix == "/submit" else {})}
        error(e.client.post("/surveys/access/unknown" + suffix, headers=e.reader, json=payload), 4040)
    ok(publish(e, form))
    ok(submit(e, form, [item(q, "答案")]))
    error(progress(e, form), 4090, "该问卷不允许重复提交")


def test_successful_progress_and_replay_renew_login_but_errors_do_not(survey_env):
    e = survey_env
    form, q = setup_form(e, required=True)
    reader_id = e.db.Users.find_one({"username": "reader"})["_id"]
    previous = e.db.Sessions.find_one({"user_id": reader_id})["expires_at"]
    e.clock.now += timedelta(hours=1)
    error(progress(e, form, [item(q, "")]), 4001)
    assert e.db.Sessions.find_one({"user_id": reader_id})["expires_at"] == previous
    ok(progress(e, form, [item(q, "答案")]))
    assert e.db.Sessions.find_one({"user_id": reader_id})["expires_at"] == e.clock.now + timedelta(days=3)
    key = str(uuid4())
    ok(submit(e, form, [item(q, "答案")], key))
    e.clock.now += timedelta(hours=1)
    ok(submit(e, form, [item(q, "答案")], key))
    assert e.db.Sessions.find_one({"user_id": reader_id})["expires_at"] == e.clock.now + timedelta(days=3)
