from datetime import timedelta
from uuid import uuid4

import pytest
from bson import ObjectId

from test_filling import item, submit
from test_question_links import content
from test_question_shares import grant, revoke, version_path
from test_surveys import add, create, error, ok, patch, publish
from test_version_import import import_version, resource


def stats(e, version, query="", headers=None):
    return e.client.get(
        version_path(version) + "/statistics" + query,
        headers=e.owner if headers is None else headers,
    )


def new_form(e, headers=None, multiple=True):
    return ok(e.client.post(
        "/surveys", headers=headers or e.owner,
        json={"title": "问卷", "allow_multiple_submissions": multiple},
    ))


def make_resource(e, key, **body):
    return ok(e.client.post(
        "/question-resources", headers=e.owner,
        json={"requestId": key, "title": "可复用题", **body},
    ))


def linked(e, version, headers=None, multiple=True):
    # 建问卷并选用该版本入卷，返回问卷与新建的卷内题。
    form = new_form(e, headers, multiple)
    question = ok(import_version(
        e, form, version["version_id"], key=f"import-{uuid4().hex[:8]}",
        headers=headers,
    ))
    return form, question


def opened(e, form, headers=None):
    ok(e.client.post(
        f"/surveys/{form['form_id']}/publish", headers=headers or e.owner
    ))
    return form


def respond(e, form, question, values, headers=None):
    for index, value in enumerate(values):
        ok(submit(e, form, [item(question, value)],
                  request_id=f"sub-{uuid4().hex[:8]}-{index}", headers=headers))


def store(e, form, question, values, offsets=None):
    # 直接写入答卷，用于构造旧数据、重复答案与非法值；不经过提交接口校验。
    documents = []
    for index, value in enumerate(values):
        offset = 0 if offsets is None else offsets[index]
        documents.append({
            "_id": ObjectId(), "form_id": ObjectId(form["form_id"]),
            "submitted_at": e.clock.now + timedelta(seconds=offset),
            "answers": [{"question_id": question["question_id"], "value": value}],
        })
    e.db.Responses.insert_many(documents)


def answered(e, version, values, kind=None, headers=None, multiple=False):
    form, question = linked(e, version, headers)
    opened(e, form, headers)
    respond(e, form, question, values, headers)
    return form, question


def option_ids(e, version):
    return [option["option_id"] for option in content(e, version)["options"]]


def test_number_statistics_counts_distribution_and_average(survey_env):
    e = survey_env
    version = resource(e, "number")
    answered(e, version, [20, 21, 30])
    data = ok(stats(e, version))
    assert set(data) == {
        "resource_id", "version_id", "version_number", "type", "title",
        "survey_count", "answer_count", "min_value", "max_value", "average",
        "values",
    }
    assert data["resource_id"] == version["resource_id"]
    assert data["version_id"] == version["version_id"]
    assert data["type"] == "number"
    assert data["survey_count"] == 1
    assert data["answer_count"] == 3
    assert data["min_value"] == "20"
    assert data["max_value"] == "30"
    assert data["average"] == pytest.approx((20 + 21 + 30) / 3)
    assert data["values"]["total"] == 3
    assert data["values"]["items"] == [
        {"value": "20", "count": 1},
        {"value": "21", "count": 1},
        {"value": "30", "count": 1},
    ]


def test_number_merges_equivalent_values_and_sorts_numerically(survey_env):
    e = survey_env
    version = resource(e, "number")
    form, question = linked(e, version)
    store(e, form, question, [9, 10, 10.0, 10.5, -0.0])
    data = ok(stats(e, version))
    assert data["answer_count"] == 5
    # 10 与 10.0 合并、负零归零，且按数值升序而非字符串序。
    assert data["values"]["items"] == [
        {"value": "0", "count": 1},
        {"value": "9", "count": 1},
        {"value": "10", "count": 2},
        {"value": "10.5", "count": 1},
    ]
    assert data["values"]["total"] == 4
    assert data["min_value"] == "0"
    assert data["max_value"] == "10.5"
    assert data["average"] == pytest.approx(7.9)


def test_single_choice_counts_and_ratio_use_answer_count(survey_env):
    e = survey_env
    version = resource(e, "single")
    form, question = linked(e, version)
    first, second = option_ids(e, version)
    store(e, form, question, [first, first, second])
    data = ok(stats(e, version))
    assert data["answer_count"] == 3
    ratios = {row["option_id"]: row["ratio"] for row in data["options"]}
    assert ratios[first] == pytest.approx(2 / 3)
    assert ratios[second] == pytest.approx(1 / 3)


def test_multiple_choice_ratio_denominator_and_invalid_values(survey_env):
    e = survey_env
    version = resource(e, "multiple")
    form, question = linked(e, version)
    first, second = option_ids(e, version)
    store(e, form, question, [
        [first, second], [first], ["不存在"], [], ["重复", "重复"], second,
    ])
    data = ok(stats(e, version))
    assert data["answer_count"] == 2
    counts = {row["option_id"]: row for row in data["options"]}
    assert counts[first]["count"] == 2
    assert counts[first]["ratio"] == pytest.approx(1.0)
    assert counts[second]["count"] == 1
    assert counts[second]["ratio"] == pytest.approx(0.5)


def test_multiple_choice_respects_selected_limits(survey_env):
    e = survey_env
    version = make_resource(
        e, "limit-key", type="multiple", options=[{"text": "甲"}, {"text": "乙"}],
        validation={"min_selected": 2, "max_selected": 2},
    )
    form, question = linked(e, version)
    first, second = option_ids(e, version)
    store(e, form, question, [[first], [first, second]])
    data = ok(stats(e, version))
    assert data["answer_count"] == 1


def test_text_statistics_order_pagination_and_out_of_range_page(survey_env):
    e = survey_env
    version = resource(e, "text")
    form, question = linked(e, version)
    store(e, form, question, ["甲", "乙", "丙", "丁"],
          offsets=[3, 1, 2, 0])
    first = ok(stats(e, version, "?page=1&page_size=2"))
    assert first["answer_count"] == 4
    assert first["contents"]["total"] == 4
    assert [row["value"] for row in first["contents"]["items"]] == ["丁", "乙"]
    beyond = ok(stats(e, version, "?page=9&page_size=2"))
    assert beyond["contents"]["items"] == []
    assert beyond["contents"]["total"] == 4


def test_number_page_beyond_range_keeps_distinct_total(survey_env):
    e = survey_env
    version = resource(e, "number")
    form, question = linked(e, version)
    store(e, form, question, [1, 2, 3])
    data = ok(stats(e, version, "?page=5&page_size=1"))
    assert data["values"]["items"] == []
    assert data["values"]["total"] == 3
    assert data["answer_count"] == 3


def test_zero_answers_returns_null_summary_and_empty_lists(survey_env):
    e = survey_env
    version = resource(e, "number")
    linked(e, version)
    data = ok(stats(e, version))
    assert data["survey_count"] == 1
    assert data["answer_count"] == 0
    assert data["min_value"] is None
    assert data["max_value"] is None
    assert data["average"] is None
    assert data["values"]["items"] == []
    assert data["values"]["total"] == 0


def test_duplicate_answers_in_same_group_are_excluded(survey_env):
    e = survey_env
    version = resource(e, "text")
    form, question = linked(e, version)
    qid = question["question_id"]
    e.db.Responses.insert_many([
        {
            "_id": ObjectId(), "form_id": ObjectId(form["form_id"]),
            "submitted_at": e.clock.now,
            "answers": [
                {"question_id": qid, "value": "重复"}, {"question_id": qid, "value": "重复"},
            ],
        },
        {
            "_id": ObjectId(), "form_id": ObjectId(form["form_id"]),
            "submitted_at": e.clock.now,
            "answers": [
                {"question_id": qid, "value": "有效"},
                {"question_id": qid, "value": "不同"},
            ],
        },
        {
            "_id": ObjectId(), "form_id": ObjectId(form["form_id"]),
            "submitted_at": e.clock.now,
            "answers": [{"question_id": qid, "value": "正常"}],
        },
    ])
    data = ok(stats(e, version))
    assert data["answer_count"] == 1
    assert [row["value"] for row in data["contents"]["items"]] == ["正常"]


def test_answer_belonging_to_another_form_is_excluded(survey_env):
    e = survey_env
    version = resource(e, "text")
    form, question = linked(e, version)
    other, other_question = linked(e, version)
    e.db.Responses.insert_one({
        "_id": ObjectId(), "form_id": ObjectId(form["form_id"]),
        "submitted_at": e.clock.now,
        "answers": [{"question_id": other_question["question_id"], "value": "错配"}],
    })
    data = ok(stats(e, version))
    assert data["survey_count"] == 2
    assert data["answer_count"] == 0


def test_inconsistent_copy_is_excluded_without_shape_change(survey_env):
    e = survey_env
    version = resource(e, "text")
    form, question = linked(e, version)
    store(e, form, question, ["漂移"])
    normal = ok(stats(e, version))
    assert normal["answer_count"] == 1
    e.db.Questions.update_one(
        {"_id": ObjectId(question["question_id"])}, {"$set": {"title": "被改动"}}
    )
    drifted = ok(stats(e, version))
    assert drifted["survey_count"] == 0
    assert drifted["answer_count"] == 0
    assert drifted["contents"]["items"] == []
    # 排除异常关联不改变响应结构，也不新增异常标记。
    assert set(drifted) == set(normal)
    assert drifted["title"] == normal["title"]
    assert e.db.Responses.count_documents({}) == 1


def test_owner_and_recipient_only_see_their_own_surveys(survey_env):
    e = survey_env
    version = resource(e, "text")
    owner_form, owner_question = answered(e, version, ["甲", "乙"])
    ok(grant(e, version, username="reader"))
    reader_form, reader_question = linked(e, version, headers=e.reader)
    opened(e, reader_form, e.reader)
    respond(e, reader_form, reader_question, ["丙"], headers=e.reader)

    mine = ok(stats(e, version))
    assert mine["survey_count"] == 1
    assert mine["answer_count"] == 2
    assert [row["value"] for row in mine["contents"]["items"]] == ["甲", "乙"]

    theirs = ok(stats(e, version, headers=e.reader))
    assert theirs["survey_count"] == 1
    assert theirs["answer_count"] == 1
    assert [row["value"] for row in theirs["contents"]["items"]] == ["丙"]


def test_revoked_recipient_keeps_existing_reference_statistics(survey_env):
    e = survey_env
    version = resource(e, "text")
    share = ok(grant(e, version, username="reader"))
    reader_form, reader_question = linked(e, version, headers=e.reader)
    opened(e, reader_form, e.reader)
    respond(e, reader_form, reader_question, ["保留"], headers=e.reader)
    ok(revoke(e, version, share))
    data = ok(stats(e, version, headers=e.reader))
    assert data["survey_count"] == 1
    assert data["answer_count"] == 1
    assert [row["value"] for row in data["contents"]["items"]] == ["保留"]


def test_without_authorization_or_reference_returns_4030(survey_env):
    e = survey_env
    version = resource(e, "text")
    error(stats(e, version, headers=e.reader), 4030)
    error(e.client.get(version_path(version) + "/statistics"), 4010)


def test_missing_resource_or_version_returns_4040(survey_env):
    e = survey_env
    version = resource(e, "text")
    error(e.client.get(
        f"/question-resources/{version['resource_id']}/versions/{ObjectId()}/statistics",
        headers=e.owner,
    ), 4040)
    error(e.client.get(
        f"/question-resources/{ObjectId()}/versions/{version['version_id']}/statistics",
        headers=e.owner,
    ), 4040)


def test_different_versions_are_not_merged(survey_env):
    e = survey_env
    first = make_resource(e, "v1-key", type="number", validation={})
    second = ok(e.client.post(
        f"/question-resources/{first['resource_id']}/versions",
        headers=e.owner,
        json={"requestId": "v2-key", "parent_version_id": first["version_id"],
              "title": "可复用题", "type": "number", "validation": {}},
    ))
    answered(e, first, [1, 2])
    answered(e, second, [7])
    assert ok(stats(e, first))["answer_count"] == 2
    assert ok(stats(e, second))["answer_count"] == 1
    assert ok(stats(e, second))["values"]["items"] == [{"value": "7", "count": 1}]


def test_number_limits_and_invalid_values_are_excluded(survey_env):
    e = survey_env
    version = make_resource(
        e, "int-key", type="number",
        validation={"min_value": 1, "max_value": 10, "integer_only": True},
    )
    form, question = linked(e, version)
    store(e, form, question, [1, 5, "7", True, 10.5, 11, 0, 6])
    data = ok(stats(e, version))
    assert data["answer_count"] == 3
    assert data["values"]["items"] == [
        {"value": "1", "count": 1},
        {"value": "5", "count": 1},
        {"value": "6", "count": 1},
    ]


def test_text_length_limits_exclude_invalid_values(survey_env):
    e = survey_env
    version = make_resource(
        e, "text-key", type="text", validation={"min_length": 2, "max_length": 4},
    )
    form, question = linked(e, version)
    store(e, form, question, ["ab", "abc", "a", "abcde", "  ", "abcd", 12])
    data = ok(stats(e, version))
    assert data["answer_count"] == 3
    assert [row["value"] for row in data["contents"]["items"]] == ["ab", "abc", "abcd"]


def test_single_choice_unknown_option_is_excluded(survey_env):
    e = survey_env
    version = resource(e, "single")
    form, question = linked(e, version)
    first = option_ids(e, version)[0]
    store(e, form, question, [first, "不存在", 3])
    data = ok(stats(e, version))
    assert data["answer_count"] == 1
    assert sum(row["count"] for row in data["options"]) == 1


def test_statistics_do_not_write_business_collections(survey_env):
    e = survey_env
    version = resource(e, "number")
    share = ok(grant(e, version, username="reader"))
    answered(e, version, [5, 6])
    before = {
        "revision": e.db.Question_forms.find_one()["revision"],
        "operations": e.db.Question_operations.count_documents({}),
        "coordination": e.db.Question_shares.find_one(
            {"_id": ObjectId(share["share_id"])}
        )["coordination_revision"],
        "responses": e.db.Responses.count_documents({}),
    }
    ok(stats(e, version))
    ok(stats(e, version, headers=e.reader))
    assert e.db.Question_forms.find_one()["revision"] == before["revision"]
    assert e.db.Question_operations.count_documents({}) == before["operations"]
    assert e.db.Question_shares.find_one(
        {"_id": ObjectId(share["share_id"])}
    )["coordination_revision"] == before["coordination"]
    assert e.db.Responses.count_documents({}) == before["responses"]


def test_answers_from_multiple_surveys_are_counted_separately(survey_env):
    e = survey_env
    version = resource(e, "text")
    answered(e, version, ["一"])
    answered(e, version, ["二", "三"])
    data = ok(stats(e, version))
    assert data["survey_count"] == 2
    assert data["answer_count"] == 3
    assert {row["value"] for row in data["contents"]["items"]} == {"一", "二", "三"}


def test_response_never_exposes_respondent_identity(survey_env):
    e = survey_env
    version = resource(e, "number")
    answered(e, version, [3])
    data = ok(stats(e, version))
    stored = e.db.Responses.find_one()
    assert stored["respondent_id"] is not None
    assert "respondent_id" not in data
    assert "respondent_username" not in data
    assert "content" not in data
    assert "source_form_id" not in data
