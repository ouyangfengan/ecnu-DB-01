from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event

import pytest
from bson import ObjectId
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from app.errors import APIError
from app.question_banks_service import QuestionBanksService
from test_filling import item, submit
from test_question_links import content
from test_question_shares import grant, reader_form, revoke
from test_surveys import add, create, deadline, error, ok, publish
from test_version_import import import_version, resource
from test_version_switch import derive_version


def bank(e, key="bank", headers=None, **fields):
    return ok(e.client.post("/question-banks", headers=headers or e.owner, json={
        "requestId": key, "name": "个人题库", **fields,
    }))


def bank_path(bank):
    return "/question-banks/" + bank["bank_id"]


def members(e, bank, headers=None, query=""):
    return e.client.get(bank_path(bank) + "/members" + query, headers=headers or e.owner)


def add_member(e, bank, version, key="add", headers=None):
    return e.client.post(bank_path(bank) + "/members", headers=headers or e.owner, json={
        "requestId": key, "version_id": version["version_id"],
    })


def switch_member(e, bank, member, expected, target, key="switch", headers=None):
    return e.client.post(
        bank_path(bank) + f"/members/{member['member_id']}/switch-version",
        headers=headers or e.owner,
        json={"requestId": key, "expected_version_id": expected, "version_id": target},
    )


def remove(e, bank, member, key="remove", headers=None):
    return e.client.post(bank_path(bank) + f"/members/{member['member_id']}/remove",
                         headers=headers or e.owner, json={"requestId": key})


def delete(e, bank, key="delete", headers=None):
    return e.client.post(bank_path(bank) + "/delete", headers=headers or e.owner,
                         json={"requestId": key})


def from_bank(e, form, bank, member, expected=None, key="from-bank", headers=None, required=False):
    return e.client.post(
        f"/surveys/{form['form_id']}/questions/from-bank", headers=headers or e.owner,
        json={"requestId": key, "bank_id": bank["bank_id"], "member_id": member["member_id"],
              "expected_member_version_id": expected or member["version_id"], "required": required},
    )


def snapshot(e):
    names = (
        "Question_banks", "Question_bank_members", "Question_forms", "Questions",
        "Question_links", "Question_resources", "Question_versions", "Question_shares",
        "Question_operations", "Responses",
    )
    return {name: list(e.db[name].find({}).sort("_id", 1)) for name in names}


def test_names_trim_before_length_description_preserved_and_duplicate_names(survey_env):
    e = survey_env
    name = "题" * 100
    description = "  " + "文" * 995 + "\n "
    first = bank(e, name=" " * 20 + name + " " * 20, description=description)
    assert first["name"] == name and first["description"] == description
    second = bank(e, key="bank2", name=name)
    assert second["bank_id"] != first["bank_id"]
    result = ok(e.client.get("/question-banks", headers=e.owner))
    assert result["total"] == 2
    assert [b["bank_id"] for b in result["items"]] == sorted(
        [first["bank_id"], second["bank_id"]], reverse=True,
    )
    assert ok(e.client.get("/question-banks", headers=e.reader))["total"] == 0
    assert ok(e.client.get("/question-banks?page=99&page_size=1", headers=e.owner)) == {
        "items": [], "total": 2, "page": 99, "page_size": 1,
    }
    indexes = e.db.Question_banks.index_information()
    assert not any(v.get("unique") for k, v in indexes.items() if k != "_id_")


@pytest.mark.parametrize("fields", [
    {"name": ""}, {"name": " \t\n "}, {"name": "a" * 101},
    {"name": 1}, {"name": None}, {"description": "a" * 1001},
    {"description": None}, {"description": False}, {"extra": "x"},
])
def test_create_input_boundaries(survey_env, fields):
    e = survey_env
    error(e.client.post("/question-banks", headers=e.owner, json={
        "requestId": "invalid", "name": "题库", **fields,
    }), 4001)
    assert e.db.Question_banks.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({}) == 0


def test_patch_clear_description_noop_timestamps_and_replay(survey_env):
    e = survey_env
    b = bank(e, description="原说明")
    e.clock.now += timedelta(seconds=1)
    payload = {"requestId": "patch", "name": " 新名称 ", "description": ""}
    first = ok(e.client.patch(bank_path(b), headers=e.owner, json=payload))
    assert first["name"] == "新名称" and first["description"] == ""
    assert first["updated_at"] != b["updated_at"]
    e.clock.now += timedelta(seconds=1)
    noop = ok(e.client.patch(bank_path(b), headers=e.owner, json={
        "requestId": "noop", "description": "",
    }))
    assert noop["changed"] is False and noop["updated_at"] == first["updated_at"]
    ok(e.client.patch(bank_path(b), headers=e.owner, json={
        "requestId": "later", "name": "后来名称",
    }))
    assert ok(e.client.patch(bank_path(b), headers=e.owner, json=payload)) == first
    for fields in ({}, {"name": None}, {"description": None}, {"name": " "},
                   {"description": "x" * 1001}, {"unknown": 1}):
        error(e.client.patch(bank_path(b), headers=e.owner, json={
            "requestId": "bad-patch", **fields,
        }), 4001)


def test_members_fixed_version_multibank_repeated_add_and_expected_switch(survey_env):
    e = survey_env
    v1 = resource(e)
    v2 = derive_version(e, v1)
    b1, b2 = bank(e), bank(e, key="bank2")
    m1 = ok(add_member(e, b1, v1))
    m2 = ok(add_member(e, b2, v2, key="second"))
    assert m1["member_id"] != m2["member_id"]
    noop = ok(add_member(e, b1, v1, key="repeat"))
    assert noop["changed"] is False
    assert noop["member_id"] == m1["member_id"]
    error(add_member(e, b1, v2, key="different"), 4090)
    error(switch_member(e, b1, m1, v2["version_id"], v2["version_id"]), 4090)
    e.clock.now += timedelta(seconds=1)
    updated = ok(switch_member(e, b1, m1, v1["version_id"], v2["version_id"]))
    assert updated["member_id"] == m1["member_id"]
    assert updated["added_at"] == m1["added_at"] and updated["updated_at"] != m1["updated_at"]
    noop = ok(switch_member(e, b1, m1, v2["version_id"], v2["version_id"], key="same"))
    assert noop["changed"] is False and noop["updated_at"] == updated["updated_at"]
    foreign = resource(e, key="foreign")
    error(switch_member(e, b1, m1, v2["version_id"], foreign["version_id"], key="cross"), 4090)
    assert ok(members(e, b2))["items"][0]["version_id"] == v2["version_id"]
    assert e.db.Question_bank_members.index_information()["unique_bank_resource"]["unique"]


def test_unavailable_member_can_switch_to_authorized_target_remove_and_delete(survey_env):
    e = survey_env
    v1 = resource(e)
    v2 = derive_version(e, v1)
    s1 = ok(grant(e, v1))
    ok(grant(e, v2, key="grant2"))
    b = bank(e, headers=e.reader)
    m = ok(add_member(e, b, v1, headers=e.reader))
    ok(revoke(e, v1, s1))
    row = ok(members(e, b, headers=e.reader))["items"][0]
    assert row["available"] is False and "title" not in row and "type" not in row
    error(add_member(e, b, v1, key="new-add", headers=e.reader), 4030)
    assert ok(add_member(e, b, v1, headers=e.reader)) == m
    error(switch_member(e, b, m, v1["version_id"], v1["version_id"], headers=e.reader), 4030)
    updated = ok(switch_member(e, b, m, v1["version_id"], v2["version_id"],
                               key="available-target", headers=e.reader))
    assert updated["version_id"] == v2["version_id"]
    assert ok(members(e, b, headers=e.reader))["items"][0]["available"]
    b2 = bank(e, key="bank2", headers=e.reader)
    # 重新授权后收录再撤销，删除不应检查版本权限。
    ok(grant(e, v1, key="reactivate"))
    m2 = ok(add_member(e, b2, v1, key="add2", headers=e.reader))
    ok(revoke(e, v1, s1, key="revoke2"))
    assert ok(remove(e, b2, m2, headers=e.reader))["deleted"]
    assert ok(delete(e, b2, headers=e.reader))["deleted"]


@pytest.mark.parametrize("corruption", ["missing_resource", "missing_version", "wrong_resource"])
def test_abnormal_members_count_as_unavailable_without_content(survey_env, corruption, monkeypatch):
    e = survey_env
    v = resource(e)
    b = bank(e)
    m = ok(add_member(e, b, v))
    if corruption == "missing_resource":
        e.db.Question_resources.delete_one({"_id": ObjectId(v["resource_id"])})
    elif corruption == "missing_version":
        e.db.Question_versions.delete_one({"_id": ObjectId(v["version_id"])})
    else:
        foreign = resource(e, key="foreign")
        e.db.Question_bank_members.update_one(
            {"_id": ObjectId(m["member_id"])},
            {"$set": {"resource_id": ObjectId(foreign["resource_id"])}},
        )
    actual = Collection.find_one

    def no_content(collection, filter, projection=None, *args, **kwargs):
        if collection.name == "Question_versions":
            assert projection == {"_id": 1, "resource_id": 1}
        return actual(collection, filter, projection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "find_one", no_content)
        result = ok(members(e, b))
    assert result["total"] == 1 and not result["items"][0]["available"]
    assert "title" not in result["items"][0]
    assert ok(members(e, b, query="?page=9&page_size=1")) == {
        "items": [], "total": 1, "page": 9, "page_size": 1,
    }
    ok(remove(e, b, m))
    ok(delete(e, b))


def test_member_pagination_stable_order_update_does_not_reorder(survey_env):
    e = survey_env
    v1 = resource(e)
    v2 = resource(e, key="resource2")
    newer = derive_version(e, v1)
    b = bank(e)
    m1 = ok(add_member(e, b, v1))
    m2 = ok(add_member(e, b, v2, key="add2"))
    expected = sorted([m1["member_id"], m2["member_id"]], reverse=True)
    e.clock.now += timedelta(seconds=1)
    ok(switch_member(e, b, m1, v1["version_id"], newer["version_id"]))
    result = ok(members(e, b))
    assert [m["member_id"] for m in result["items"]] == expected
    assert all(m["available"] and set(m).isdisjoint({"content", "source_form_id"}) for m in result["items"])
    for page, member in enumerate(expected, 1):
        result = ok(members(e, b, query=f"?page={page}&page_size=1"))
        assert result["total"] == 2 and result["items"][0]["member_id"] == member
    assert ok(members(e, b, query="?page=3&page_size=1"))["total"] == 2


def test_remove_delete_replay_and_new_requests_not_found_path_mismatch(survey_env, monkeypatch):
    e = survey_env
    v = resource(e)
    b, b2 = bank(e), bank(e, key="bank2")
    m = ok(add_member(e, b, v))
    error(remove(e, b2, m), 4040)
    error(switch_member(e, b2, m, v["version_id"], v["version_id"]), 4040)
    first = ok(remove(e, b, m))
    error(remove(e, b, m, key="new-remove"), 4040)
    gone = ok(delete(e, b))
    error(delete(e, b, key="new-delete"), 4040)
    error(e.client.get(bank_path(b), headers=e.owner), 4040)
    actual = Collection.find_one

    def only_operations(collection, *args, **kwargs):
        if collection.name.startswith("Question_") and collection.name != "Question_operations":
            raise AssertionError("成功回放不读取已删除对象或授权")
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "find_one", only_operations)
        assert ok(remove(e, b, m)) == first
        assert ok(delete(e, b)) == gone
        assert ok(add_member(e, b, v)) == m
    error(add_member(e, b, v, key="new-add"), 4040)


@pytest.mark.parametrize("kind", ["text", "number", "single", "multiple"])
def test_bank_import_preserves_fixed_content_id_rules_and_replay_after_delete(survey_env, kind, monkeypatch):
    e = survey_env
    v = resource(e, kind)
    b = bank(e)
    m = ok(add_member(e, b, v))
    form = create(e)
    old = ok(add(e, form))
    result = ok(from_bank(e, form, b, m, required=True))
    assert result["version_id"] == v["version_id"] and result["question_id"] != old["question_id"]
    assert result["bank_id"] == b["bank_id"] and result["member_id"] == m["member_id"]
    assert result["validation"]["required"] is True
    assert result["order"] == 2 and result["jump_rules"] == []
    version_content = content(e, v)
    assert result["options"] == version_content["options"]
    assert result["title"] == version_content["title"] and result["type"] == kind
    assert result["validation"] == {**version_content["validation"], "required": True}
    before = snapshot(e)
    error(from_bank(e, form, b, m, key="duplicate"), 4090)
    assert snapshot(e) == before
    # 直接版本入卷与题库入卷共用卷内重复规则。
    error(import_version(e, form, v["version_id"], key="direct-duplicate"), 4090)
    ok(publish(e, form))
    ok(delete(e, b))
    actual = Collection.find_one

    def no_current_lookup(collection, *args, **kwargs):
        if collection.name in ("Question_banks", "Question_bank_members", "Question_versions", "Question_shares"):
            raise AssertionError("入卷回放不能重新解析成员")
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "find_one", no_current_lookup)
        assert ok(from_bank(e, form, b, m, required=True)) == result
    error(from_bank(e, form, b, m, required=True, key="new"), 4040)


def test_membership_does_not_grant_access_and_bank_delete_preserves_answers(survey_env):
    e = survey_env
    v = resource(e)
    share = ok(grant(e, v))
    b = bank(e, headers=e.reader)
    m = ok(add_member(e, b, v, headers=e.reader))
    form = reader_form(e)
    q = ok(from_bank(e, form, b, m, headers=e.reader))
    ok(revoke(e, v, share))
    error(from_bank(e, reader_form(e), b, m, key="new", headers=e.reader), 4030)
    assert ok(from_bank(e, form, b, m, headers=e.reader)) == q
    ok(e.client.post(f"/surveys/{form['form_id']}/publish", headers=e.reader))
    ok(submit(e, form, [item(q, "答复")], headers=e.owner))
    before = snapshot(e)
    gone = ok(delete(e, b, headers=e.reader))
    assert gone["removed_member_count"] == 1
    after = snapshot(e)
    for name in before:
        if name not in ("Question_banks", "Question_bank_members", "Question_operations"):
            assert after[name] == before[name]
    assert e.db.Responses.find_one()["answers"] == [item(q, "答复")]


def test_import_checks_expected_version_and_does_not_resolve_new_member_version(survey_env):
    e = survey_env
    v1 = resource(e)
    v2 = derive_version(e, v1)
    b = bank(e)
    m = ok(add_member(e, b, v1))
    form = create(e)
    updated = ok(switch_member(e, b, m, v1["version_id"], v2["version_id"]))
    before = snapshot(e)
    error(from_bank(e, form, b, m), 4090)
    assert snapshot(e) == before
    q = ok(from_bank(e, form, b, updated))
    assert q["version_id"] == v2["version_id"]


@pytest.mark.parametrize("operation", ["create", "patch", "add", "switch", "remove", "delete", "import"])
def test_result_failure_rolls_back_every_business_write(survey_env, monkeypatch, operation):
    e = survey_env
    v1 = resource(e)
    v2 = derive_version(e, v1)
    b = bank(e)
    m = ok(add_member(e, b, v1))
    form = create(e)
    other = resource(e, key="resource2")

    def perform():
        if operation == "create":
            return e.client.post("/question-banks", headers=e.owner,
                                 json={"requestId": "fail", "name": "新库"})
        if operation == "patch":
            return e.client.patch(bank_path(b), headers=e.owner,
                                  json={"requestId": "fail", "name": "更名"})
        if operation == "add":
            return add_member(e, b, other, key="fail")
        if operation == "switch":
            return switch_member(e, b, m, v1["version_id"], v2["version_id"], key="fail")
        if operation == "remove":
            return remove(e, b, m, key="fail")
        if operation == "delete":
            return delete(e, b, key="fail")
        return from_bank(e, form, b, m, key="fail")

    before = snapshot(e)
    actual = Collection.update_one

    def fail_result(collection, filter, update, *args, **kwargs):
        if collection.name == "Question_operations" and "result" in update.get("$set", {}):
            raise APIError(4090, "模拟去重结果写入失败", 409)
        return actual(collection, filter, update, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "update_one", fail_result)
        error(perform(), 4090)
    assert snapshot(e) == before
    ok(perform())


@pytest.mark.parametrize("same_key", [False, True])
def test_concurrent_member_adds_preserve_one_relation(survey_env, same_key):
    e = survey_env
    v = resource(e)
    b = bank(e)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = [ok(r) for r in pool.map(
            lambda i: add_member(e, b, v, key="same" if same_key else f"add-{i}"), range(3),
        )]
    assert e.db.Question_bank_members.count_documents({}) == 1
    assert len({r["member_id"] for r in results}) == 1
    if same_key:
        assert all(r == results[0] for r in results)
    else:
        assert sum(r["changed"] for r in results) == 1


def test_unique_key_retry_retains_authorization_binding(survey_env, monkeypatch):
    e = survey_env
    v = resource(e)
    share = ok(grant(e, v))
    b = bank(e, headers=e.reader)
    actual_insert = Collection.insert_one
    transaction = QuestionBanksService.transaction
    failed = []

    def fail_member_once(collection, *args, **kwargs):
        if collection.name == "Question_bank_members" and not failed:
            failed.append(True)
            raise DuplicateKeyError("模拟成员唯一键竞争", details={
                "keyPattern": {"bank_id": 1, "resource_id": 1},
            })
        return actual_insert(collection, *args, **kwargs)

    def reauthorize_after_abort(service, callback):
        try:
            return transaction(service, callback)
        except DuplicateKeyError:
            ok(revoke(e, v, share))
            ok(grant(e, v, key="reactivate"))
            raise

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "insert_one", fail_member_once)
        patch.setattr(QuestionBanksService, "transaction", reauthorize_after_abort)
        error(add_member(e, b, v, headers=e.reader), 4090)
    assert e.db.Question_banks.find_one()["revision"] == 0
    assert e.db.Question_shares.find_one()["coordination_revision"] == 0
    assert e.db.Question_bank_members.count_documents({}) == 0
    assert e.db.Question_operations.count_documents({"request_id": "add"}) == 0
    ok(add_member(e, b, v, headers=e.reader))


def test_real_unique_key_retry_rechecks_existing_member(survey_env, monkeypatch):
    e = survey_env
    v = resource(e)
    b = bank(e)
    m = ok(add_member(e, b, v))
    actual = Collection.find_one
    reads = []

    def miss_once(collection, *args, **kwargs):
        if collection.name == "Question_bank_members":
            reads.append(True)
            if len(reads) == 1:
                return None
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "find_one", miss_once)
        result = ok(add_member(e, b, v, key="different"))
    assert result["member_id"] == m["member_id"] and result["changed"] is False
    assert len(reads) == 2
    assert e.db.Question_bank_members.count_documents({}) == 1


@pytest.mark.parametrize("mutation", ["switch", "remove", "delete"])
def test_member_mutation_wins_import_rechecks_in_transaction(survey_env, monkeypatch, mutation):
    e = survey_env
    v1 = resource(e)
    v2 = derive_version(e, v1)
    b = bank(e)
    m = ok(add_member(e, b, v1))
    form = create(e)
    entered, resume = Event(), Event()
    coordinate = QuestionBanksService.coordinate_bank

    def pause_first(service, *args, **kwargs):
        if not entered.is_set():
            entered.set()
            assert resume.wait(15)
        return coordinate(service, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(QuestionBanksService, "coordinate_bank", pause_first)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(from_bank, e, form, b, m)
            try:
                assert entered.wait(10)
                if mutation == "switch":
                    ok(switch_member(e, b, m, v1["version_id"], v2["version_id"]))
                elif mutation == "remove":
                    ok(remove(e, b, m))
                else:
                    ok(delete(e, b))
            finally:
                resume.set()
            error(pending.result(timeout=20), 4090 if mutation == "switch" else 4040)
    assert e.db.Questions.count_documents({}) == 0
    assert e.db.Question_forms.find_one()["revision"] == 0
    assert e.db.Question_operations.count_documents({"request_id": "from-bank"}) == 0


@pytest.mark.parametrize("operation", ["add", "switch", "import"])
def test_authorization_auto_retry_cannot_adopt_reenabled_grant(survey_env, monkeypatch, operation):
    e = survey_env
    v1 = resource(e)
    v2 = derive_version(e, v1)
    share = ok(grant(e, v1))
    ok(grant(e, v2, key="grant2"))
    b = bank(e, headers=e.reader)
    if operation != "add":
        m = ok(add_member(e, b, v2 if operation == "switch" else v1, headers=e.reader))
    form = reader_form(e)
    before_bank = e.db.Question_banks.find_one()
    entered, resume = Event(), Event()
    actual = Collection.update_one
    revisions = []

    def pause_guard(collection, filter, update, *args, **kwargs):
        if (collection.name == "Question_shares" and filter.get("_id") == ObjectId(share["share_id"])
                and "coordination_revision" in update.get("$inc", {})):
            revisions.append(filter["authorization_revision"])
            if not entered.is_set():
                entered.set()
                assert resume.wait(15)
        return actual(collection, filter, update, *args, **kwargs)

    def perform():
        if operation == "add":
            return add_member(e, b, v1, key="pending", headers=e.reader)
        if operation == "switch":
            return switch_member(e, b, m, v2["version_id"], v1["version_id"],
                                 key="pending", headers=e.reader)
        return from_bank(e, form, b, m, key="pending", headers=e.reader)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "update_one", pause_guard)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(perform)
            try:
                assert entered.wait(10)
                ok(revoke(e, v1, share))
                ok(grant(e, v1, key="reactivate"))
            finally:
                resume.set()
            error(pending.result(timeout=20), 4090)
    assert revisions and set(revisions) == {1}
    assert e.db.Question_banks.find_one() == before_bank
    assert e.db.Question_forms.find_one()["revision"] == 0
    assert e.db.Question_operations.count_documents({"request_id": "pending"}) == 0
    ok(perform())


def test_member_list_count_uses_snapshot_during_removal(survey_env, monkeypatch):
    e = survey_env
    v = resource(e)
    b = bank(e)
    m = ok(add_member(e, b, v))
    entered, resume = Event(), Event()
    actual = Collection.count_documents

    def pause_count(collection, *args, **kwargs):
        if collection.name == "Question_bank_members" and not entered.is_set():
            entered.set()
            assert resume.wait(15)
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "count_documents", pause_count)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(members, e, b)
            try:
                assert entered.wait(10)
                ok(remove(e, b, m))
            finally:
                resume.set()
            result = ok(pending.result(timeout=20))
    assert result["total"] == len(result["items"]) == 1
    assert ok(members(e, b))["total"] == 0


def test_private_banks_authentication_scopes_and_import_input(survey_env):
    e = survey_env
    v = resource(e)
    b = bank(e)
    m = ok(add_member(e, b, v))
    form = create(e)
    error(e.client.get("/question-banks"), 4010)
    for url in (bank_path(b), bank_path(b) + "/members"):
        error(e.client.get(url, headers=e.reader), 4030)
    error(add_member(e, b, v, headers=e.reader), 4030)
    error(remove(e, b, m, headers=e.reader), 4030)
    error(delete(e, b, headers=e.reader), 4030)
    error(from_bank(e, form, b, m, headers=e.reader), 4030)
    reader_bank = bank(e, key="reader-bank", headers=e.reader)
    own_v = resource(e, key="reader-resource", headers=e.reader)
    own_m = ok(add_member(e, reader_bank, own_v, key="reader-add", headers=e.reader))
    error(from_bank(e, form, reader_bank, own_m, headers=e.reader), 4030)
    for missing in ("bank_id", "member_id", "expected_member_version_id", "required", "requestId"):
        payload = {
            "requestId": "bad", "bank_id": b["bank_id"], "member_id": m["member_id"],
            "expected_member_version_id": v["version_id"], "required": False,
        }
        payload.pop(missing)
        error(e.client.post(f"/surveys/{form['form_id']}/questions/from-bank",
                            headers=e.owner, json=payload), 4001)
    for query in ("?page=0", "?page_size=101", "?page=abc"):
        error(members(e, b, query=query), 4001)
        error(e.client.get("/question-banks" + query, headers=e.owner), 4001)
    spec = e.app.openapi()
    operations = [(p, method) for p, methods in spec["paths"].items()
                  for method in methods if p.startswith("/question-banks") or p.endswith("/from-bank")]
    assert len(operations) == 10
    assert all(spec["paths"][p][method].get("security") for p, method in operations)


@pytest.mark.parametrize("same_key", [False, True])
def test_concurrent_bank_imports_replay_or_reject_duplicate(survey_env, same_key):
    e = survey_env
    v = resource(e)
    b = bank(e)
    m = ok(add_member(e, b, v))
    form = create(e)
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(
            lambda i: from_bank(e, form, b, m, key="same" if same_key else f"import-{i}"),
            range(3),
        ))
    assert e.db.Questions.count_documents({}) == e.db.Question_links.count_documents({}) == 1
    if same_key:
        values = [ok(r) for r in results]
        assert all(v == values[0] for v in values)
    else:
        assert sum(r.json()["code"] == 0 for r in results) == 1
        for r in results:
            if r.json()["code"]:
                error(r, 4090)
    assert e.db.Question_forms.find_one()["revision"] == 1
    assert e.db.Question_banks.find_one()["revision"] == 2


@pytest.mark.parametrize("state", ["published", "closed", "expired"])
def test_bank_import_rejects_nondraft_without_partial_revisions(survey_env, state):
    e = survey_env
    v = resource(e)
    b = bank(e)
    m = ok(add_member(e, b, v))
    form = create(e)
    ok(add(e, form))
    if state == "expired":
        ok(deadline(e, form, (e.clock.now + timedelta(seconds=1)).isoformat()))
    ok(publish(e, form))
    if state == "closed":
        ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
    if state == "expired":
        e.clock.now += timedelta(seconds=2)
    before = snapshot(e)
    error(from_bank(e, form, b, m), 4090)
    assert snapshot(e) == before


def test_shared_bank_import_link_failure_rolls_back_both_revisions_and_grant(survey_env, monkeypatch):
    e = survey_env
    v = resource(e)
    ok(grant(e, v))
    b = bank(e, headers=e.reader)
    m = ok(add_member(e, b, v, headers=e.reader))
    form = reader_form(e)
    before = snapshot(e)
    actual = Collection.insert_one

    def fail_link(collection, *args, **kwargs):
        if collection.name == "Question_links":
            raise APIError(4090, "模拟入卷关联失败", 409)
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Collection, "insert_one", fail_link)
        error(from_bank(e, form, b, m, headers=e.reader), 4090)
    assert snapshot(e) == before
    ok(from_bank(e, form, b, m, headers=e.reader))


def test_empty_member_list_and_unknown_ids(survey_env):
    e = survey_env
    b = bank(e)
    assert ok(members(e, b, query="?page=9&page_size=1")) == {
        "items": [], "total": 0, "page": 9, "page_size": 1,
    }
    error(e.client.get("/question-banks/invalid", headers=e.owner), 4001)
    error(e.client.get("/question-banks/" + str(ObjectId()), headers=e.owner), 4040)
    error(add_member(e, b, {"version_id": str(ObjectId())}), 4040)
    v = resource(e)
    error(from_bank(e, create(e), b, {"member_id": str(ObjectId()), "version_id": v["version_id"]}), 4040)
