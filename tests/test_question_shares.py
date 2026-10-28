from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, Event
from types import SimpleNamespace

import pytest
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from app.errors import APIError
from app.question_links_service import QuestionLinksService
from app.question_resource_schemas import ResourceCreate
from app.question_shares_service import QuestionSharesService
from test_filling import item, submit
from test_question_links import link, path, required, save, save_and_link
from test_surveys import add, create, error, ok
from test_version_import import import_version, resource
from test_version_switch import derive_version, switch


def version_path(version):
    return f"/question-resources/{version['resource_id']}/versions/{version['version_id']}"


def grant(e, version, key="grant", username="reader", headers=None):
    return e.client.post(
        version_path(version) + "/shares",
        headers=e.owner if headers is None else headers,
        json={"requestId": key, "recipient_username": username},
    )


def revoke(e, version, share, key="revoke", headers=None):
    return e.client.post(
        version_path(version) + f"/shares/{share['share_id']}/revoke",
        headers=e.owner if headers is None else headers, json={"requestId": key},
    )


def received(e, headers=None, query=""):
    return e.client.get(
        "/question-shares/received" + query,
        headers=e.reader if headers is None else headers,
    )


def read(e, version, headers=None):
    return e.client.get(
        version_path(version), headers=e.reader if headers is None else headers,
    )


def fork(e, version, key="fork", headers=None, **fields):
    body = ok(read(e, version, e.owner))["content"]
    return e.client.post(
        version_path(version) + "/fork",
        headers=e.reader if headers is None else headers,
        json={"requestId": key, **body, **fields},
    )


def reader_form(e):
    return ok(e.client.post("/surveys", headers=e.reader, json={"title": "接收者问卷"}))


def stored_share(e, share):
    return e.db.Question_shares.find_one({"_id": ObjectId(share["share_id"])})


def test_grant_revoke_reactivation_noops_and_historical_replay(survey_env, monkeypatch):
    e = survey_env
    version = resource(e)
    first = ok(grant(e, version, username=" reader "))
    assert first["authorization_revision"] == 1
    assert first["changed"] and first["status"] == "active"
    before = stored_share(e, first)
    e.clock.now += timedelta(seconds=1)
    noop = ok(grant(e, version, key="grant-noop"))
    assert noop["changed"] is False
    assert stored_share(e, first) == before
    removed = ok(revoke(e, version, first))
    assert removed["status"] == "revoked" and removed["authorization_revision"] == 2
    after = stored_share(e, first)
    e.clock.now += timedelta(seconds=1)
    assert ok(revoke(e, version, first, key="revoke-noop"))["changed"] is False
    assert stored_share(e, first) == after
    assert ok(received(e))["items"] == []
    restored = ok(grant(e, version, key="reactivate"))
    assert restored["share_id"] == first["share_id"]
    assert restored["authorization_revision"] == 3
    assert restored["authorized_at"] != first["authorized_at"]
    assert restored["revoked_at"] == removed["revoked_at"]
    current = stored_share(e, first)
    actual = Collection.find_one

    def replay_only(collection, *args, **kwargs):
        if collection.name in ("Question_shares", "Question_resources", "Question_versions"):
            raise AssertionError("成功回放不得查询当前授权")
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "find_one", replay_only)
        assert ok(revoke(e, version, first)) == removed
        assert ok(grant(e, version, username=" reader ")) == first
    assert stored_share(e, first) == current
    sent = ok(e.client.get(version_path(version) + "/shares", headers=e.owner))
    assert sent["items"][0]["status"] == "active"
    assert sent["items"][0]["authorization_revision"] == 3
    error(grant(e, version, key="revoke"), 4090)


def test_recipient_read_whitelist_and_no_history_or_response_permissions(survey_env):
    e = survey_env
    form = create(e)
    q = ok(add(e, form))
    first = ok(save_and_link(e, form, q))
    second = derive_version(e, first)
    share = ok(grant(e, first))
    owner_result = ok(read(e, first, e.owner))
    assert owner_result["source_form_id"] == form["form_id"]
    result = ok(read(e, first))
    assert set(result) == {"resource_id", "version_id", "version_number", "created_at", "content"}
    assert result["content"] == owner_result["content"]
    error(read(e, second), 4030)
    third = derive_version(e, first, key="future-version")
    error(read(e, third), 4030)
    error(e.client.get(f"/question-resources/{first['resource_id']}", headers=e.reader), 4030)
    assert ok(e.client.get("/question-resources", headers=e.reader))["total"] == 0
    for route in [
        f"/surveys/{form['form_id']}",
        f"/surveys/{form['form_id']}/statistics",
        path(form, q) + "/statistics",
        version_path(first) + "/shares",
    ]:
        error(e.client.get(route, headers=e.reader), 4030)
    error(grant(e, first, key="reshare", username="owner", headers=e.reader), 4030)
    error(e.client.post(
        f"/question-resources/{first['resource_id']}/versions", headers=e.reader,
        json={"requestId": "unauthorized-derive", "parent_version_id": first["version_id"],
              **result["content"]},
    ), 4030)
    error(e.client.post(
        version_path(first) + "/restore", headers=e.reader,
        json={"requestId": "unauthorized-restore"},
    ), 4030)
    ok(revoke(e, first, share))
    error(read(e, first), 4030)


def test_received_list_is_active_only_paginated_and_use_does_not_reorder(survey_env):
    e = survey_env
    first = resource(e)
    second = resource(e, key="second-resource")
    a = ok(grant(e, first))
    e.clock.now += timedelta(seconds=1)
    b = ok(grant(e, second, key="second-grant"))
    before = ok(received(e))
    assert [v["version_id"] for v in before["items"]] == [
        second["version_id"], first["version_id"],
    ]
    assert set(before["items"][0]) == {
        "share_id", "resource_id", "version_id", "version_number", "title", "type",
        "owner_username", "authorized_at", "authorization_revision",
    }
    assert ok(received(e, e.owner))["total"] == 0
    form = reader_form(e)
    e.clock.now += timedelta(seconds=1)
    ok(import_version(e, form, first["version_id"], headers=e.reader))
    assert ok(received(e)) == before
    assert stored_share(e, a)["coordination_revision"] == 1
    assert stored_share(e, a)["authorization_revision"] == 1
    page = ok(received(e, query="?page=2&page_size=1"))
    assert page["total"] == 2 and page["items"][0]["version_id"] == first["version_id"]
    ok(revoke(e, second, b))
    assert ok(received(e))["total"] == 1
    error(received(e, query="?page_size=101"), 4001)


@pytest.mark.parametrize("kind", ["text", "number", "single", "multiple"])
def test_fork_creates_independent_owned_resource_and_preserves_provenance(survey_env, kind):
    e = survey_env
    original = resource(e, kind)
    share = ok(grant(e, original))
    result = ok(fork(e, original))
    stored = e.db.Question_versions.find_one({"_id": ObjectId(result["version_id"])})
    assert stored["source_resource_id"] == ObjectId(original["resource_id"])
    assert stored["source_version_id"] == ObjectId(original["version_id"])
    assert stored["parent_version_id"] is None
    assert "source_form_id" not in stored
    assert stored["content"] == ok(read(e, original))["content"]
    assert e.db.Question_resources.find_one({"_id": stored["resource_id"]})["owner_id"] == (
        e.db.Users.find_one({"username": "reader"})["_id"]
    )
    ok(revoke(e, original, share))
    assert ok(read(e, result))["source_version_id"] == original["version_id"]
    assert ok(fork(e, original)) == result
    error(fork(e, original, key="new-fork"), 4030)
    error(read(e, original), 4030)
    independent_share = ok(grant(e, result, key="share-own", username="owner", headers=e.reader))
    assert independent_share["changed"]
    # 来源只作追溯；接收新资源不获得其上游原版本的权限。
    assert ok(read(e, result, e.owner))["content"] == stored["content"]
    form = reader_form(e)
    ok(import_version(e, form, result["version_id"], key="own-import", headers=e.reader))


@pytest.mark.parametrize("validation", [
    {"min": 0}, {"max": 120}, {"integer": True}, {"required": False},
])
def test_fork_rejects_aliases_and_required_and_rolls_back(survey_env, validation):
    e = survey_env
    original = resource(e, "number")
    share = ok(grant(e, original))
    before = stored_share(e, share)
    error(fork(e, original, validation=validation), 4001)
    assert stored_share(e, share) == before
    assert e.db.Question_resources.count_documents({}) == 1
    assert e.db.Question_operations.count_documents({"request_id": "fork"}) == 0
    assert ok(fork(e, original, validation={
        "min_value": 0, "max_value": 120, "integer_only": True,
    }))["source_version_id"] == original["version_id"]


def test_fork_option_ids_follow_existing_derivation_rules(survey_env):
    e = survey_env
    original = resource(e, "single")
    ok(grant(e, original))
    options = ok(read(e, original))["content"]["options"]
    error(fork(e, original, options=[{**options[0], "text": "改名"}, options[1]]), 4001)
    copied = ok(fork(e, original, options=[options[0], {"text": "新增"}]))
    actual = ok(read(e, copied))["content"]["options"]
    assert actual[0] == options[0]
    assert actual[1]["option_id"] not in {o["option_id"] for o in options}


def test_shared_import_link_and_switch_keep_ownership_and_target_permissions(survey_env):
    e = survey_env
    original = resource(e)
    target = derive_version(e, original, title="新题")
    a = ok(grant(e, original))
    form = reader_form(e)
    q = ok(import_version(e, form, original["version_id"], headers=e.reader))
    error(import_version(e, form, original["version_id"], key="duplicate", headers=e.reader), 4090)
    error(switch(e, form, q, original["version_id"], target["version_id"], headers=e.reader), 4030)
    b = ok(grant(e, target, key="target-grant"))
    ok(revoke(e, original, a))
    result = ok(switch(e, form, q, original["version_id"], target["version_id"], headers=e.reader))
    assert result["question_id"] == q["question_id"]
    assert result["version_id"] == target["version_id"]
    ok(revoke(e, target, b, key="target-revoke"))
    noop = ok(switch(e, form, q, target["version_id"], target["version_id"],
                     key="noop", headers=e.reader))
    assert noop["changed"] is False
    error(switch(e, form, q, target["version_id"], original["version_id"],
                 key="back", headers=e.reader), 4030)
    error(e.client.post(
        path(form, q) + "/derive-and-switch", headers=e.reader,
        json={"requestId": "derive-shared", "expected_version_id": target["version_id"],
              "parent_version_id": target["version_id"], "title": "新题", "type": "text"},
    ), 4030)
    error(import_version(e, create(e), target["version_id"], key="foreign-survey", headers=e.reader), 4030)
    ok(grant(e, target, key="reactivate-target"))
    unlinked = ok(e.client.post(
        f"/surveys/{form['form_id']}/questions", headers=e.reader,
        json={"title": "新题", "type": "text"},
    ))
    linked = ok(link(e, form, unlinked, target["version_id"], headers=e.reader))
    assert ok(link(e, form, unlinked, target["version_id"], headers=e.reader)) == linked
    ok(revoke(e, target, b, key="revoke-again"))
    error(link(e, form, unlinked, target["version_id"], headers=e.reader), 4030)


def test_revoked_copy_can_edit_publish_fill_save_and_share_independent_resource(survey_env):
    e = survey_env
    original = resource(e, "single")
    share = ok(grant(e, original))
    form = reader_form(e)
    q = ok(import_version(e, form, original["version_id"], required=True, headers=e.reader))
    ok(revoke(e, original, share))
    before = e.db.Question_links.find_one()
    ok(required(e, form, q, False, headers=e.reader))
    jumps = [{"condition": {"op": "eq", "value": q["options"][0]["option_id"]},
              "target": "end"}]
    ok(e.client.patch(path(form, q), headers=e.reader, json={"jump_rules": jumps}))
    error(e.client.patch(path(form, q), headers=e.reader, json={"title": "直接改题干"}), 4090)
    error(e.client.patch(path(form, q), headers=e.reader, json={"jump_rules": [
        {"condition": {"op": "eq", "value": q["options"][0]["option_id"]},
         "target": str(ObjectId())},
    ]}), 4001)
    ok(e.client.post(f"/surveys/{form['form_id']}/publish", headers=e.reader))
    ok(submit(e, form, [item(q, q["options"][0]["option_id"])], headers=e.owner))
    result = ok(save(e, form, q, headers=e.reader))
    assert result["source_resource_id"] == original["resource_id"]
    assert result["source_version_id"] == original["version_id"]
    assert result["source_form_id"] == form["form_id"]
    assert e.db.Question_links.find_one() == before
    original_content = ok(read(e, original, e.owner))["content"]
    assert ok(read(e, result))["content"] == original_content
    ok(grant(e, result, key="reshare-copy", username="owner", headers=e.reader))
    receiver = ok(read(e, result, e.owner))
    assert set(receiver) == {"resource_id", "version_id", "version_number", "created_at", "content"}
    assert ok(e.client.get(
        f"/surveys/{form['form_id']}/statistics", headers=e.reader,
    ))
    error(e.client.get(f"/surveys/{form['form_id']}/statistics", headers=e.owner), 4030)
    assert ok(import_version(e, form, original["version_id"], required=True, headers=e.reader)) == q


@pytest.mark.parametrize("same_key", [False, True])
def test_concurrent_first_grants_create_one_record(survey_env, same_key):
    e = survey_env
    original = resource(e)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(
            lambda i: grant(e, original, key="same" if same_key else f"grant-{i}"),
            range(4),
        ))
    results = [ok(response) for response in responses]
    assert len({r["share_id"] for r in results}) == 1
    assert e.db.Question_shares.count_documents({}) == 1
    assert stored_share(e, results[0])["authorization_revision"] == 1
    if same_key:
        assert all(r == results[0] for r in results)
    else:
        assert sum(r["changed"] for r in results) == 1
    assert e.db.Question_operations.count_documents({}) == (2 if same_key else 5)


def test_unique_grant_race_reenters_transaction(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    rendezvous = Barrier(2)
    actual = Collection.insert_one

    def simultaneous_insert(collection, *args, **kwargs):
        if collection.name == "Question_shares":
            rendezvous.wait(timeout=10)
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "insert_one", simultaneous_insert)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda i: grant(e, original, key=f"race-{i}"), range(2)))
    assert sorted(ok(r)["changed"] for r in responses) == [False, True]
    assert e.db.Question_shares.count_documents({}) == 1


@pytest.mark.parametrize("operation", ["import", "fork", "link", "switch"])
@pytest.mark.parametrize("reactivate", [False, True])
def test_bound_use_cannot_cross_revocation_or_reactivation(
    survey_env, monkeypatch, operation, reactivate,
):
    e = survey_env
    original = resource(e)
    form = reader_form(e)
    if operation == "switch":
        prior = derive_version(e, original)
        ok(grant(e, prior, key="prior-grant"))
        q = ok(import_version(e, form, prior["version_id"], key="prior-import", headers=e.reader))
    elif operation == "link":
        q = ok(e.client.post(
            f"/surveys/{form['form_id']}/questions", headers=e.reader,
            json={"title": "可复用题", "type": "text"},
        ))
    share = ok(grant(e, original))
    before_form = e.db.Question_forms.find_one({"_id": ObjectId(form["form_id"])})
    entered, resume = Event(), Event()
    actual = Collection.update_one
    intercepted = []

    def pause_bound_use(collection, filter, update, *args, **kwargs):
        if (collection.name == "Question_shares"
                and "coordination_revision" in update.get("$inc", {})):
            intercepted.append(filter["authorization_revision"])
            if not entered.is_set():
                entered.set()
                assert resume.wait(15)
        return actual(collection, filter, update, *args, **kwargs)

    def perform():
        if operation == "import":
            return import_version(e, form, original["version_id"], headers=e.reader)
        if operation == "fork":
            return fork(e, original)
        if operation == "link":
            return link(e, form, q, original["version_id"], headers=e.reader)
        return switch(e, form, q, prior["version_id"], original["version_id"], headers=e.reader)

    with monkeypatch.context() as m:
        m.setattr(Collection, "update_one", pause_bound_use)
        with ThreadPoolExecutor(max_workers=1) as pool:
            task = pool.submit(perform)
            try:
                assert entered.wait(10)
                ok(revoke(e, original, share))
                if reactivate:
                    ok(grant(e, original, key="reactivate"))
            finally:
                resume.set()
            error(task.result(timeout=20), 4090)
    assert intercepted and set(intercepted) == {1}
    assert e.db.Question_forms.find_one({"_id": before_form["_id"]}) == before_form
    assert stored_share(e, share)["coordination_revision"] == 0
    if reactivate:
        assert perform().json()["code"] == 0
    else:
        error(perform(), 4030)


def test_binding_is_local_even_when_service_instance_is_reused(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    service = QuestionSharesService(SimpleNamespace(app=e.app))
    reader_id = e.db.Users.find_one({"username": "reader"})["_id"]
    data = ResourceCreate.model_validate({
        "requestId": "service-fork", "title": "复制", "type": "text",
    })
    actual = Collection.update_one
    calls = []

    def deny_first_guard(collection, filter, update, *args, **kwargs):
        if collection.name == "Question_shares" and "coordination_revision" in update.get("$inc", {}):
            calls.append(filter["authorization_revision"])
            raise APIError(4090, "模拟授权竞争", 409)
        return actual(collection, filter, update, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "update_one", deny_first_guard)
        with pytest.raises(APIError) as exc:
            service.fork(original["resource_id"], original["version_id"], data, reader_id)
        assert exc.value.code == 4090
    ok(revoke(e, original, share))
    ok(grant(e, original, key="reactivate"))
    result = service.fork(original["resource_id"], original["version_id"], data, reader_id)
    assert result["source_version_id"] == original["version_id"]
    assert calls == [1]
    assert stored_share(e, share)["authorization_revision"] == 3


def test_link_unique_retry_does_not_return_without_permission_recheck(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    ok(grant(e, original))
    form = reader_form(e)
    q = ok(e.client.post(
        f"/surveys/{form['form_id']}/questions", headers=e.reader,
        json={"title": "可复用题", "type": "text"},
    ))
    actual = Collection.insert_one
    failures = []

    def fail_first_link(collection, *args, **kwargs):
        if collection.name == "Question_links" and not failures:
            failures.append(True)
            raise DuplicateKeyError("模拟关联唯一键竞争", details={"keyPattern": {"question_id": 1}})
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "insert_one", fail_first_link)
        assert ok(link(e, form, q, original["version_id"], headers=e.reader))["version_id"] == (
            original["version_id"]
        )
    assert e.db.Question_links.count_documents({}) == 1
    assert e.db.Question_shares.find_one()["coordination_revision"] == 1


def test_fork_failure_rolls_back_resource_version_marker_and_coordination(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    before = stored_share(e, share)
    actual = Collection.insert_one

    def fail_version(collection, *args, **kwargs):
        if collection.name == "Question_versions":
            raise APIError(4090, "模拟版本写入失败", 409)
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "insert_one", fail_version)
        error(fork(e, original), 4090)
    assert e.db.Question_resources.count_documents({}) == 1
    assert e.db.Question_versions.count_documents({}) == 1
    assert e.db.Question_operations.count_documents({"request_id": "fork"}) == 0
    assert stored_share(e, share) == before
    ok(fork(e, original))


def test_missing_permission_and_invalid_grant_do_not_create_records(survey_env):
    e = survey_env
    original = resource(e)
    error(grant(e, original, headers={}), 4010)
    error(grant(e, original, headers=e.reader), 4030)
    error(grant(e, original, username="missing"), 4040)
    error(grant(e, original, username="Reader"), 4040)
    error(grant(e, original, username="owner"), 4001)
    error(grant(e, original, username="  "), 4001)
    error(grant(e, original, username=123), 4001)
    error(read(e, original), 4030)
    error(fork(e, original), 4030)
    assert e.db.Question_shares.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({}) == 1
    fake = {**original, "version_id": str(ObjectId())}
    error(grant(e, fake), 4040)
    error(read(e, fake), 4040)
    share = ok(grant(e, original))
    error(revoke(e, original, share, headers=e.reader), 4030)
    error(revoke(e, original, {"share_id": str(ObjectId())}), 4040)
    assert e.db.Question_shares.index_information()["unique_version_recipient"]["unique"]


@pytest.mark.parametrize("operation", ["import", "fork", "switch", "revoke"])
def test_concurrent_same_request_replays_shared_operation_once(survey_env, operation):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    form = reader_form(e)
    if operation == "switch":
        prior = derive_version(e, original)
        ok(grant(e, prior, key="prior-grant"))
        q = ok(import_version(e, form, prior["version_id"], key="prior-import", headers=e.reader))

    def perform(_):
        if operation == "import":
            return import_version(e, form, original["version_id"], headers=e.reader)
        if operation == "fork":
            return fork(e, original)
        if operation == "switch":
            return switch(e, form, q, prior["version_id"], original["version_id"], headers=e.reader)
        return revoke(e, original, share)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = [ok(r) for r in pool.map(perform, range(3))]
    assert all(r == results[0] for r in results)
    stored = stored_share(e, share)
    assert stored["coordination_revision"] == (0 if operation == "revoke" else 1)
    assert stored["authorization_revision"] == (2 if operation == "revoke" else 1)


def test_fork_replay_precedes_authorization_binding(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    payload = {"requestId": "fork", **ok(read(e, original))["content"]}
    first = ok(e.client.post(version_path(original) + "/fork", headers=e.reader, json=payload))
    ok(revoke(e, original, share))
    actual = Collection.find_one

    def no_authorization_reads(collection, *args, **kwargs):
        if collection.name in ("Question_resources", "Question_versions", "Question_shares"):
            raise AssertionError("回放不能绑定授权或重新读取版本")
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "find_one", no_authorization_reads)
        assert ok(e.client.post(
            version_path(original) + "/fork", headers=e.reader, json=payload,
        )) == first


@pytest.mark.parametrize("operation", ["grant", "revoke"])
def test_authorization_and_operation_record_commit_atomically(survey_env, monkeypatch, operation):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original)) if operation == "revoke" else None
    before = stored_share(e, share) if share else None
    actual = Collection.update_one

    def fail_result(collection, filter, update, *args, **kwargs):
        if collection.name == "Question_operations" and "result" in update.get("$set", {}):
            raise APIError(4090, "模拟去重结果写入失败", 409)
        return actual(collection, filter, update, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "update_one", fail_result)
        response = grant(e, original) if operation == "grant" else revoke(e, original, share)
        error(response, 4090)
    assert e.db.Question_operations.count_documents({"request_id": operation}) == 0
    if share:
        assert stored_share(e, share) == before
        ok(revoke(e, original, share))
    else:
        assert e.db.Question_shares.count_documents({}) == 0
        ok(grant(e, original))


def test_lineage_does_not_grant_upstream_access_to_new_recipient(survey_env):
    e = survey_env
    credentials = {"username": "third", "password": "secret"}
    ok(e.client.post("/auth/register", json=credentials))
    token = ok(e.client.post("/auth/login", json=credentials))["token"]
    third = {"Authorization": "Bearer " + token}
    original = resource(e)
    ok(grant(e, original))
    copied = ok(fork(e, original))
    ok(grant(e, copied, username="third", key="share-third", headers=e.reader))
    assert ok(read(e, copied, third))["content"] == ok(read(e, copied))["content"]
    error(read(e, original, third), 4030)
    error(e.client.get(f"/question-resources/{copied['resource_id']}", headers=third), 4030)


def test_link_unique_retry_keeps_bound_revision_after_reauthorization(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    form = reader_form(e)
    q = ok(e.client.post(
        f"/surveys/{form['form_id']}/questions", headers=e.reader,
        json={"title": "可复用题", "type": "text"},
    ))
    failures = []
    actual = Collection.insert_one
    transaction = QuestionLinksService.transaction

    def unique_conflict(collection, *args, **kwargs):
        if collection.name == "Question_links" and not failures:
            failures.append(True)
            raise DuplicateKeyError("模拟唯一键竞争", details={"keyPattern": {"question_id": 1}})
        return actual(collection, *args, **kwargs)

    def change_authorization_after_abort(service, callback):
        try:
            return transaction(service, callback)
        except DuplicateKeyError:
            # 事务已回滚并释放授权写锁，在唯一键重试前更换授权期间。
            ok(revoke(e, original, share))
            ok(grant(e, original, key="reactivate"))
            raise

    with monkeypatch.context() as m:
        m.setattr(Collection, "insert_one", unique_conflict)
        m.setattr(QuestionLinksService, "transaction", change_authorization_after_abort)
        error(link(e, form, q, original["version_id"], headers=e.reader), 4090)
    assert stored_share(e, share)["authorization_revision"] == 3
    assert stored_share(e, share)["coordination_revision"] == 0
    assert e.db.Question_links.count_documents({}) == 0
    ok(link(e, form, q, original["version_id"], headers=e.reader))


def test_grant_unique_key_error_is_retried_without_refreshing_times(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    before = stored_share(e, share)
    actual = Collection.find_one
    reads = []

    def miss_existing_share_once(collection, *args, **kwargs):
        if collection.name == "Question_shares":
            reads.append(True)
            if len(reads) == 1:
                return None
        return actual(collection, *args, **kwargs)

    e.clock.now += timedelta(seconds=1)
    with monkeypatch.context() as m:
        m.setattr(Collection, "find_one", miss_existing_share_once)
        result = ok(grant(e, original, key="different-request"))
    assert len(reads) == 2
    assert result["changed"] is False
    assert stored_share(e, share) == before
    assert e.db.Question_shares.count_documents({}) == 1


def test_read_uses_snapshot_when_revocation_commits_during_response(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    entered, resume = Event(), Event()
    actual = Collection.find_one

    def pause_read_after_authorization(collection, *args, **kwargs):
        result = actual(collection, *args, **kwargs)
        if collection.name == "Question_shares" and kwargs.get("session") and not entered.is_set():
            entered.set()
            assert resume.wait(15)
        return result

    with monkeypatch.context() as m:
        m.setattr(Collection, "find_one", pause_read_after_authorization)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(read, e, original)
            try:
                assert entered.wait(10)
                ok(revoke(e, original, share))
            finally:
                resume.set()
            assert ok(pending.result(timeout=20))["version_id"] == original["version_id"]
    error(read(e, original), 4030)


def test_shared_import_failure_rolls_back_both_revisions(survey_env, monkeypatch):
    e = survey_env
    original = resource(e)
    share = ok(grant(e, original))
    form = reader_form(e)
    before_share = stored_share(e, share)
    before_form = e.db.Question_forms.find_one({"_id": ObjectId(form["form_id"])})
    actual = Collection.insert_one

    def fail_link(collection, *args, **kwargs):
        if collection.name == "Question_links":
            raise APIError(4090, "模拟关联写入失败", 409)
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as m:
        m.setattr(Collection, "insert_one", fail_link)
        error(import_version(e, form, original["version_id"], headers=e.reader), 4090)
    assert stored_share(e, share) == before_share
    assert e.db.Question_forms.find_one({"_id": before_form["_id"]}) == before_form
    assert e.db.Questions.count_documents({}) == 0
    assert e.db.Question_links.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({"request_id": "import-key"}) == 0
