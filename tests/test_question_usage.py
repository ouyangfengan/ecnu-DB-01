from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from threading import Event

import pytest
from bson import ObjectId
from pymongo.collection import Collection

from test_question_links import save, save_and_link
from test_question_shares import fork, grant, read, reader_form, revoke
from test_surveys import add, create, deadline, error, ok, publish
from test_version_import import import_version, resource
from test_version_switch import derive_version, switch


def usage(e, version, resource_level=False, headers=None, query=""):
    url = f"/question-resources/{version['resource_id']}"
    if not resource_level:
        url += f"/versions/{version['version_id']}"
    return e.client.get(
        url + "/usage" + query, headers=e.owner if headers is None else headers,
    )


def legacy_duplicate(e, question, order=None):
    original = e.db.Questions.find_one({"_id": ObjectId(question["question_id"])})
    copy = deepcopy(original)
    copy["_id"] = ObjectId()
    copy["order"] = order if order is not None else original["order"] + 10
    e.db.Questions.insert_one(copy)
    link = e.db.Question_links.find_one({"question_id": original["_id"]})
    link.pop("_id")
    link["question_id"] = copy["_id"]
    e.db.Question_links.insert_one(link)
    return copy


@pytest.mark.parametrize("resource_level", [False, True])
def test_empty_usage_and_empty_facets(survey_env, resource_level):
    e = survey_env
    original = resource(e)
    result = ok(usage(e, original, resource_level))
    assert result["scope"] == "owner"
    assert result["survey_count"] == result["own_survey_count"] == result["other_survey_count"] == 0
    assert result["own_surveys"] == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert ("version_id" in result) is not resource_level
    beyond = ok(usage(e, original, resource_level, query="?page=9&page_size=1"))
    assert beyond["own_surveys"] == {"items": [], "total": 0, "page": 9, "page_size": 1}


def test_resource_and_version_counts_deduplicate_forms_independently(survey_env):
    e = survey_env
    original = resource(e)
    second = derive_version(e, original)
    form = create(e)
    first_q = ok(import_version(e, form, original["version_id"], key="first"))
    second_q = ok(import_version(e, form, second["version_id"], key="second"))
    repeated = legacy_duplicate(e, first_q)
    result = ok(usage(e, original, True))
    assert result["survey_count"] == 1
    row = result["own_surveys"]["items"][0]
    assert row["form_id"] == form["form_id"]
    assert row["questions"] == [
        {"question_id": first_q["question_id"], "version_id": original["version_id"]},
        {"question_id": second_q["question_id"], "version_id": second["version_id"]},
        {"question_id": str(repeated["_id"]), "version_id": original["version_id"]},
    ]
    a, b = ok(usage(e, original)), ok(usage(e, second))
    assert a["survey_count"] == b["survey_count"] == 1
    assert result["survey_count"] != a["survey_count"] + b["survey_count"]


@pytest.mark.parametrize("resource_level", [False, True])
def test_pagination_out_of_range_keeps_counts_and_stable_form_order(survey_env, resource_level):
    e = survey_env
    original = resource(e)
    forms = []
    for i in range(3):
        form = create(e, title=f"本人{i}")
        ok(import_version(e, form, original["version_id"], key=f"import-{i}"))
        forms.append(form)
    # 同创建时间仍按 ObjectId 倒序；测试固定创建时间。
    expected = sorted([f["form_id"] for f in forms], reverse=True)
    pages = [ok(usage(e, original, resource_level, query=f"?page={p}&page_size=1"))
             for p in (1, 2, 3, 4)]
    assert [p["own_surveys"]["items"][0]["form_id"] for p in pages[:3]] == expected
    assert all(p["own_surveys"]["total"] == p["survey_count"] == 3 for p in pages)
    assert pages[-1]["own_surveys"]["items"] == []


def test_question_order_ties_use_id_and_old_missing_creation_time(survey_env):
    e = survey_env
    original = resource(e)
    form = create(e)
    question = ok(import_version(e, form, original["version_id"]))
    # 仅随机测试库撤掉顺序约束，模拟迁移前存在的同序旧题。
    e.db.Questions.drop_index("unique_form_order")
    extra = legacy_duplicate(e, question, order=question["order"])
    e.db.Question_forms.update_one(
        {"_id": ObjectId(form["form_id"])}, {"$unset": {"created_at": ""}}
    )
    row = ok(usage(e, original))["own_surveys"]["items"][0]
    assert [q["question_id"] for q in row["questions"]] == sorted([
        question["question_id"], str(extra["_id"]),
    ])


def test_owner_anonymous_summary_and_self_only_response(survey_env):
    e = survey_env
    original = resource(e)
    own = create(e)
    ok(import_version(e, own, original["version_id"], key="own-import"))
    ok(grant(e, original))
    for i in range(2):
        other = reader_form(e)
        ok(import_version(e, other, original["version_id"], key=f"reader-{i}", headers=e.reader))
    result = ok(usage(e, original, True))
    assert set(result) == {
        "resource_id", "scope", "survey_count", "own_survey_count",
        "other_survey_count", "own_surveys",
    }
    assert (result["survey_count"], result["own_survey_count"], result["other_survey_count"]) == (3, 1, 2)
    assert result["own_surveys"]["items"][0]["form_id"] == own["form_id"]
    assert set(result["own_surveys"]["items"][0]) == {"form_id", "title", "status", "questions"}
    self_result = ok(usage(e, original, headers=e.reader))
    assert set(self_result) == {
        "resource_id", "version_id", "scope", "own_survey_count", "own_surveys",
    }
    assert self_result["scope"] == "self" and self_result["own_survey_count"] == 2
    error(usage(e, original, True, headers=e.reader), 4030)


@pytest.mark.parametrize("resource_level", [False, True])
def test_only_other_usage_keeps_empty_own_page_and_nonzero_summary(survey_env, resource_level):
    e = survey_env
    original = resource(e)
    ok(grant(e, original))
    form = reader_form(e)
    q = ok(import_version(e, form, original["version_id"], headers=e.reader))
    legacy_duplicate(e, q)
    result = ok(usage(e, original, resource_level, query="?page=99&page_size=1"))
    assert result["survey_count"] == result["other_survey_count"] == 1
    assert result["own_survey_count"] == 0
    assert result["own_surveys"] == {"items": [], "total": 0, "page": 99, "page_size": 1}


def test_authorization_does_not_expose_usage_of_other_versions(survey_env):
    e = survey_env
    original = resource(e)
    second = derive_version(e, original)
    ok(grant(e, original))
    form = create(e)
    ok(import_version(e, form, second["version_id"]))
    assert ok(usage(e, original, headers=e.reader))["own_survey_count"] == 0
    error(usage(e, second, headers=e.reader), 4030)
    error(usage(e, original, True, headers=e.reader), 4030)


def test_authorized_empty_then_revoked_existing_reference_and_last_reference_removed(survey_env):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    empty = ok(usage(e, original, headers=e.reader))
    assert empty["own_survey_count"] == 0 and empty["own_surveys"]["items"] == []
    form = reader_form(e)
    q = ok(import_version(e, form, original["version_id"], headers=e.reader))
    ok(revoke(e, original, share))
    result = ok(usage(e, original, headers=e.reader, query="?page=999&page_size=1"))
    assert result["own_survey_count"] == result["own_surveys"]["total"] == 1
    assert result["own_surveys"]["items"] == []
    error(read(e, original), 4030)
    error(import_version(e, reader_form(e), original["version_id"], key="new-import", headers=e.reader), 4030)
    # 项目没有删题 API；只在随机库模拟旧数据中的题目移除。
    e.db.Questions.delete_one({"_id": ObjectId(q["question_id"])})
    error(usage(e, original, headers=e.reader), 4030)
    assert ok(usage(e, original))["other_survey_count"] == 0


def test_revoked_nonrecipient_with_existing_own_reference_can_query_only_self(survey_env):
    e = survey_env
    original = resource(e)
    form = reader_form(e)
    q = ok(e.client.post(
        f"/surveys/{form['form_id']}/questions", headers=e.reader,
        json={"title": "已有旧副本", "type": "text"},
    ))
    e.db.Question_links.insert_one({
        "resource_id": ObjectId(original["resource_id"]),
        "version_id": ObjectId(original["version_id"]),
        "form_id": ObjectId(form["form_id"]), "question_id": ObjectId(q["question_id"]),
    })
    assert e.db.Question_shares.count_documents({}) == 0
    assert ok(usage(e, original, headers=e.reader))["own_survey_count"] == 1
    error(read(e, original), 4030)


@pytest.mark.parametrize("corruption", [
    "missing_question", "missing_form", "foreign_question", "missing_version", "foreign_version",
])
def test_orphan_and_mismatched_links_are_not_counted(survey_env, corruption):
    e = survey_env
    original = resource(e)
    form = create(e)
    question = ok(import_version(e, form, original["version_id"]))
    link = e.db.Question_links.find_one()
    if corruption == "missing_question":
        e.db.Questions.delete_one({"_id": link["question_id"]})
    elif corruption == "missing_form":
        e.db.Question_forms.delete_one({"_id": link["form_id"]})
    elif corruption == "foreign_question":
        e.db.Questions.update_one({"_id": link["question_id"]}, {"$set": {"form_id": ObjectId()}})
    else:
        foreign = resource(e, key="foreign") if corruption == "foreign_version" else None
        e.db.Question_links.update_one(
            {"_id": link["_id"]},
            {"$set": {"version_id": ObjectId(foreign["version_id"]) if foreign else ObjectId()}},
        )
    for resource_level in (False, True):
        result = ok(usage(e, original, resource_level))
        assert result["survey_count"] == 0 and result["own_surveys"]["items"] == []
    assert e.db.Question_links.count_documents({}) == 1


def test_orphan_reference_does_not_grant_post_revocation_query_permission(survey_env):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    form = reader_form(e)
    q = ok(import_version(e, form, original["version_id"], headers=e.reader))
    ok(revoke(e, original, share))
    e.db.Questions.delete_one({"_id": ObjectId(q["question_id"])})
    error(usage(e, original, headers=e.reader), 4030)


def test_switch_and_delete_change_current_counts_not_historical_usage(survey_env):
    e = survey_env
    original = resource(e)
    second = derive_version(e, original)
    form = create(e)
    q = ok(import_version(e, form, original["version_id"]))
    ok(switch(e, form, q, original["version_id"], second["version_id"]))
    assert ok(usage(e, original))["survey_count"] == 0
    assert ok(usage(e, second))["survey_count"] == 1
    assert ok(usage(e, original, True))["survey_count"] == 1
    e.db.Questions.delete_one({"_id": ObjectId(q["question_id"])})
    assert ok(usage(e, second))["survey_count"] == 0
    assert ok(usage(e, original, True))["survey_count"] == 0


def test_grant_save_and_fork_provenance_do_not_count_as_original_usage(survey_env):
    e = survey_env
    original = resource(e)
    ok(grant(e, original))
    derived = ok(fork(e, original))
    form = reader_form(e)
    ok(import_version(e, form, derived["version_id"], headers=e.reader))
    assert ok(usage(e, original, True))["survey_count"] == 0
    assert ok(usage(e, derived, True, headers=e.reader))["survey_count"] == 1
    own_form = create(e)
    q = ok(add(e, own_form))
    saved = ok(save(e, own_form, q))
    assert ok(usage(e, saved, True))["survey_count"] == 0
    associated = ok(save_and_link(e, own_form, q, key="associate"))
    assert ok(usage(e, associated, True))["survey_count"] == 1


@pytest.mark.parametrize("state", ["draft", "published", "closed", "expired"])
def test_all_states_count_and_effective_status_is_preserved(survey_env, state):
    e = survey_env
    original = resource(e)
    form = create(e)
    ok(import_version(e, form, original["version_id"]))
    if state != "draft":
        if state == "expired":
            ok(deadline(e, form, (e.clock.now + timedelta(seconds=1)).isoformat()))
        ok(publish(e, form))
        if state == "closed":
            ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
        if state == "expired":
            e.clock.now += timedelta(seconds=2)
    result = ok(usage(e, original))
    assert result["survey_count"] == 1
    assert result["own_surveys"]["items"][0]["status"] == ("closed" if state == "expired" else state)


def test_projections_self_path_and_no_answers_or_business_writes(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    ok(grant(e, original))
    form = reader_form(e)
    ok(import_version(e, form, original["version_id"], headers=e.reader))
    before = {
        name: list(e.db[name].find({})) for name in (
            "Question_forms", "Questions", "Question_resources", "Question_versions",
            "Question_links", "Question_shares", "Question_operations",
        )
    }
    actual_aggregate, actual_find_one, actual_update = (
        Collection.aggregate, Collection.find_one, Collection.update_one,
    )
    pipelines = []

    def inspect_aggregate(collection, pipeline, *args, **kwargs):
        assert collection.name != "Responses"
        if collection.name == "Question_links":
            pipelines.append(pipeline)
            assert kwargs.get("session") is not None
            is_own = any("$facet" in stage for stage in pipeline)
            for stage in pipeline:
                if "$lookup" not in stage:
                    continue
                lookup = stage["$lookup"]
                assert "$project" in lookup["pipeline"][1]
                projection = lookup["pipeline"][1]["$project"]
                if lookup["from"] == "Question_versions":
                    assert projection == {"_id": 1, "resource_id": 1}
                if lookup["from"] == "Question_forms":
                    if is_own:
                        assert "owner_id" in lookup["pipeline"][0]["$match"]
                        assert set(projection) == {
                            "_id", "owner_id", "title", "status", "deadline", "created_at",
                        }
                    else:
                        assert projection == {"_id": 1, "owner_id": 1}
        return actual_aggregate(collection, pipeline, *args, **kwargs)

    def inspect_find_one(collection, filter, projection=None, *args, **kwargs):
        assert collection.name != "Responses"
        if collection.name == "Question_versions":
            assert projection == {"_id": 1, "resource_id": 1}
        return actual_find_one(collection, filter, projection, *args, **kwargs)

    def no_business_updates(collection, *args, **kwargs):
        assert collection.name == "Sessions"  # 登录会话续期仍保留，不属于业务写入。
        return actual_update(collection, *args, **kwargs)

    def reject_writes(collection, *args, **kwargs):
        raise AssertionError("使用查询不能写业务集合")

    with monkeypatch.context() as m:
        m.setattr(Collection, "aggregate", inspect_aggregate)
        m.setattr(Collection, "find_one", inspect_find_one)
        m.setattr(Collection, "update_one", no_business_updates)
        for method in (
            "insert_one", "insert_many", "delete_one", "delete_many", "update_many",
            "replace_one", "find_one_and_update", "bulk_write",
        ):
            m.setattr(Collection, method, reject_writes)
        ok(usage(e, original, headers=e.reader))
        assert len(pipelines) == 1 and any("$facet" in s for s in pipelines[0])
        ok(usage(e, original))
        assert len(pipelines) == 3
    assert {
        name: list(e.db[name].find({})) for name in before
    } == before


def test_count_and_items_share_snapshot_during_delete(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    form = create(e)
    q = ok(import_version(e, form, original["version_id"]))
    entered, resume = Event(), Event()
    actual = Collection.aggregate

    def pause_after_own_result(collection, pipeline, *args, **kwargs):
        result = actual(collection, pipeline, *args, **kwargs)
        if collection.name == "Question_links" and any("$facet" in s for s in pipeline):
            rows = list(result)
            if not entered.is_set():
                entered.set()
                assert resume.wait(15)
            return iter(rows)
        return result

    with monkeypatch.context() as m:
        m.setattr(Collection, "aggregate", pause_after_own_result)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(usage, e, original)
            try:
                assert entered.wait(10)
                e.db.Questions.delete_one({"_id": ObjectId(q["question_id"])})
            finally:
                resume.set()
            result = ok(pending.result(timeout=20))
    assert result["survey_count"] == result["own_surveys"]["total"] == 1
    assert len(result["own_surveys"]["items"]) == 1
    assert ok(usage(e, original))["survey_count"] == 0


def test_authorization_and_usage_share_snapshot_during_revocation(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    entered, resume = Event(), Event()
    actual = Collection.aggregate

    def pause_own(collection, *args, **kwargs):
        result = actual(collection, *args, **kwargs)
        if collection.name == "Question_links" and not entered.is_set():
            entered.set()
            assert resume.wait(15)
        return result

    with monkeypatch.context() as m:
        m.setattr(Collection, "aggregate", pause_own)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(usage, e, original, headers=e.reader)
            try:
                assert entered.wait(10)
                ok(revoke(e, original, share))
            finally:
                resume.set()
            assert ok(pending.result(timeout=20))["own_survey_count"] == 0
    error(usage(e, original, headers=e.reader), 4030)


@pytest.mark.parametrize("query", [
    "?page=0", "?page_size=0", "?page_size=101", "?page=abc",
])
def test_usage_pagination_validation(survey_env, query):
    e = survey_env
    original = resource(e)
    error(usage(e, original, query=query), 4001)
    error(usage(e, original, True, query=query), 4001)


def test_login_existence_scopes_and_nonunique_indexes(survey_env):
    e = survey_env
    original = resource(e)
    foreign = resource(e, key="foreign")
    error(usage(e, original, headers={}), 4010)
    error(usage(e, original, True, headers={}), 4010)
    error(usage(e, original, headers=e.reader), 4030)
    error(usage(e, original, True, headers=e.reader), 4030)
    error(usage(e, {**original, "resource_id": "invalid"}), 4001)
    error(usage(e, {**original, "version_id": "invalid"}), 4001)
    error(usage(e, {**original, "resource_id": str(ObjectId())}, True), 4040)
    error(usage(e, {**original, "version_id": str(ObjectId())}), 4040)
    error(usage(e, {**original, "version_id": foreign["version_id"]}), 4040)
    indexes = e.db.Question_links.index_information()
    assert indexes["unique_question_link"]["unique"]
    assert not indexes["resource_usage"].get("unique", False)
    assert indexes["resource_usage"]["key"] == [
        ("resource_id", 1), ("form_id", 1), ("question_id", 1),
    ]
    assert indexes["version_usage"]["key"] == [
        ("resource_id", 1), ("version_id", 1), ("form_id", 1), ("question_id", 1),
    ]
    spec = e.app.openapi()
    routes = [p for p in spec["paths"] if p.endswith("/usage")]
    assert len(routes) == 2
    assert all(spec["paths"][p]["get"]["security"] for p in routes)
