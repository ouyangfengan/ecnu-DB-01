from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from bson import ObjectId
from pymongo.collection import Collection

from app.errors import APIError
from test_question_links import content, path, source
from test_surveys import add, create, deadline, detail, error, ok, patch, publish
from test_version_import import import_version, resource


def derive_version(e, original, key="derive", **fields):
    return ok(e.client.post(
        f"/question-resources/{original['resource_id']}/versions", headers=e.owner,
        json={"requestId": key, "parent_version_id": original["version_id"],
              **content(e, original), **fields},
    ))


def setup(e, kind="text"):
    original = resource(e, kind)
    form = create(e)
    question = ok(import_version(e, form, original["version_id"], required=True))
    return form, question, original


def switch(e, form, question, expected, target, key="switch", headers=None):
    return e.client.post(
        path(form, question) + "/switch-version",
        headers=e.owner if headers is None else headers,
        json={"requestId": key, "expected_version_id": expected, "version_id": target},
    )


def derive_switch(e, form, question, expected, parent, key="derive-switch", **fields):
    return e.client.post(
        path(form, question) + "/derive-and-switch", headers=e.owner,
        json={"requestId": key, "expected_version_id": expected,
              "parent_version_id": parent["version_id"],
              **content(e, parent), **fields},
    )


@pytest.mark.parametrize("kind", ["text", "number", "single", "multiple"])
def test_switch_preserves_id_order_required_and_immutable_versions(survey_env, kind):
    e = survey_env
    form, question, original = setup(e, kind)
    second = derive_version(e, original, title="第二版")
    before_content = content(e, original)
    before_link = e.db.Question_links.find_one()
    result = ok(switch(e, form, question, original["version_id"], second["version_id"]))
    assert result["changed"] is True
    assert result["question_id"] == question["question_id"]
    assert result["order"] == question["order"]
    assert result["validation"]["required"] is True
    assert result["options"] == content(e, second)["options"]
    assert result["version_id"] == second["version_id"]
    assert result["title"] == "第二版"
    assert result["jump_rules"] == []
    after_link = e.db.Question_links.find_one()
    assert {**before_link, "version_id": ObjectId(second["version_id"])} == after_link
    assert content(e, original) == before_content
    assert e.db.Questions.count_documents({}) == 1


def test_retains_incoming_and_outgoing_jumps_and_rolls_back_invalid_switch(survey_env):
    e = survey_env
    original = resource(e, "single")
    form = create(e)
    prior = ok(add(e, form, "number"))
    question = ok(import_version(e, form, original["version_id"], required=True))
    last = ok(add(e, form))
    selected = question["options"][0]["option_id"]
    incoming = [{"condition": {"op": "eq", "value": 1}, "target": question["question_id"]}]
    outgoing = [{"condition": {"op": "eq", "value": selected}, "target": last["question_id"]}]
    ok(patch(e, form, prior, jump_rules=incoming))
    ok(patch(e, form, question, jump_rules=outgoing))
    good = derive_version(e, original, title="保持选项")
    result = ok(switch(e, form, question, original["version_id"], good["version_id"]))
    assert result["jump_rules"] == outgoing
    assert detail(e, form)["questions"][0]["jump_rules"] == incoming
    bad = derive_version(e, original, key="bad-version",
                         options=[{"text": "新甲"}, {"text": "新乙"}])
    before_q = e.db.Questions.find_one({"_id": ObjectId(question["question_id"])})
    before_link = e.db.Question_links.find_one()
    before_form = e.db.Question_forms.find_one()
    error(switch(e, form, question, good["version_id"], bad["version_id"], key="bad-switch"), 4001)
    assert e.db.Questions.find_one({"_id": before_q["_id"]}) == before_q
    assert e.db.Question_links.find_one() == before_link
    assert e.db.Question_forms.find_one() == before_form
    assert e.db.Question_versions.find_one({"_id": ObjectId(bad["version_id"])})


def test_same_version_noop_and_replay_after_subsequent_switch_and_publication(
    survey_env, monkeypatch,
):
    e = survey_env
    form, question, original = setup(e)
    before_q = e.db.Questions.find_one()
    before_link = e.db.Question_links.find_one()
    revision = e.db.Question_forms.find_one()["revision"]
    noop = ok(switch(e, form, question, original["version_id"], original["version_id"], key="noop"))
    assert noop["changed"] is False
    assert e.db.Questions.find_one() == before_q
    assert e.db.Question_links.find_one() == before_link
    assert e.db.Question_forms.find_one()["revision"] == revision + 1
    second = derive_version(e, original, title="第二版")
    first_switch = ok(switch(e, form, question, original["version_id"], second["version_id"]))
    ok(switch(e, form, question, second["version_id"], original["version_id"], key="back"))
    ok(publish(e, form))
    ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
    actual = Collection.find_one

    def replay_only(collection, *args, **kwargs):
        if collection.name in ("Questions", "Question_links", "Question_forms", "Question_versions"):
            raise AssertionError("成功重试不能重新读取当前状态")
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Collection, "find_one", replay_only)
        assert ok(switch(e, form, question, original["version_id"], second["version_id"])) == first_switch
        assert ok(switch(e, form, question, original["version_id"], original["version_id"], key="noop")) == noop
    assert source(e, form, question).json()["data"]["version_id"] == original["version_id"]
    error(switch(e, form, question, original["version_id"], original["version_id"], key="new"), 4090)
    error(switch(e, form, question, second["version_id"], original["version_id"]), 4090)


def test_expected_version_cross_resource_and_duplicate_target_conflicts(survey_env):
    e = survey_env
    form, question, original = setup(e)
    second = derive_version(e, original, title="第二版")
    other = ok(import_version(e, form, second["version_id"], key="second-import"))
    foreign = resource(e, key="other-resource")
    for expected, target in [
        (second["version_id"], original["version_id"]),
        (original["version_id"], foreign["version_id"]),
        (original["version_id"], second["version_id"]),
    ]:
        error(switch(e, form, question, expected, target), 4090)
    assert other["version_id"] == second["version_id"]
    assert source(e, form, question).json()["data"]["version_id"] == original["version_id"]
    assert e.db.Question_operations.count_documents({"request_id": "switch"}) == 0


def test_derive_and_switch_from_arbitrary_old_parent_is_atomic_and_retryable(survey_env):
    e = survey_env
    form, question, original = setup(e)
    second = derive_version(e, original, title="第二版")
    ok(switch(e, form, question, original["version_id"], second["version_id"]))
    result = ok(derive_switch(e, form, question, second["version_id"], original, title="从旧版派生"))
    assert result["changed"] is True
    assert result["question_id"] == question["question_id"]
    stored = e.db.Question_versions.find_one({"_id": ObjectId(result["version_id"])})
    assert stored["parent_version_id"] == ObjectId(original["version_id"])
    assert stored["version_number"] == 3
    assert stored["content"]["title"] == "从旧版派生"
    assert "expected_version_id" not in stored["content"]
    assert "required" not in stored["content"]["validation"]
    ok(publish(e, form))
    assert ok(derive_switch(
        e, form, question, second["version_id"], original, title="从旧版派生",
    )) == result
    assert e.db.Question_versions.count_documents({}) == 3


def test_derive_invalid_jump_rolls_back_new_version_sequence_and_all_mutations(survey_env):
    e = survey_env
    form, question, original = setup(e, "single")
    outgoing = [{"condition": {"op": "eq", "value": question["options"][0]["option_id"]},
                 "target": "end"}]
    ok(patch(e, form, question, jump_rules=outgoing))
    before_form = e.db.Question_forms.find_one()
    before_question = e.db.Questions.find_one()
    before_link = e.db.Question_links.find_one()
    error(derive_switch(e, form, question, original["version_id"], original,
                        options=[{"text": "新甲"}, {"text": "新乙"}]), 4001)
    assert e.db.Question_forms.find_one() == before_form
    assert e.db.Questions.find_one() == before_question
    assert e.db.Question_links.find_one() == before_link
    assert e.db.Question_versions.count_documents({}) == 1
    assert e.db.Question_resources.find_one()["last_version_number"] == 1
    assert e.db.Question_operations.count_documents({"request_id": "derive-switch"}) == 0
    assert ok(derive_switch(e, form, question, original["version_id"], original,
                            title="保留选项"))["changed"]


def test_derive_link_write_failure_rolls_back_version_and_question(survey_env, monkeypatch):
    e = survey_env
    form, question, original = setup(e)
    before_q = e.db.Questions.find_one()
    before_form = e.db.Question_forms.find_one()
    actual = Collection.update_one

    def fail_link(collection, *args, **kwargs):
        if collection.name == "Question_links":
            raise APIError(4090, "模拟关联更新失败", 409)
        return actual(collection, *args, **kwargs)

    with monkeypatch.context() as patcher:
        patcher.setattr(Collection, "update_one", fail_link)
        error(derive_switch(e, form, question, original["version_id"], original,
                            title="新版"), 4090)
    assert e.db.Questions.find_one() == before_q
    assert e.db.Question_forms.find_one() == before_form
    assert e.db.Question_versions.count_documents({}) == 1
    assert e.db.Question_resources.find_one()["last_version_number"] == 1
    assert source(e, form, question).json()["data"]["version_id"] == original["version_id"]


@pytest.mark.parametrize("state", ["published", "closed", "expired"])
def test_non_draft_rejects_first_switch_and_derive(survey_env, state):
    e = survey_env
    form, question, original = setup(e)
    if state == "expired":
        end = e.clock.now + timedelta(hours=1)
        ok(deadline(e, form, end.isoformat()))
    ok(publish(e, form))
    if state == "closed":
        ok(e.client.post(f"/surveys/{form['form_id']}/close", headers=e.owner))
    elif state == "expired":
        e.clock.now = end
    error(switch(e, form, question, original["version_id"], original["version_id"]), 4090)
    error(derive_switch(e, form, question, original["version_id"], original), 4090)
    assert e.db.Question_versions.count_documents({}) == 1


def test_permissions_unlinked_missing_and_strict_request_contract(survey_env):
    e = survey_env
    form, question, original = setup(e)
    error(switch(e, form, question, original["version_id"], original["version_id"], headers={}), 4010)
    error(switch(e, form, question, original["version_id"], original["version_id"], headers=e.reader), 4030)
    error(switch(e, form, question, original["version_id"], str(ObjectId())), 4040)
    unlinked = ok(add(e, form))
    error(switch(e, form, unlinked, original["version_id"], original["version_id"]), 4090)
    base = {"requestId": "request", "version_id": original["version_id"]}
    error(e.client.post(path(form, question) + "/switch-version",
                        headers=e.owner, json=base), 4001)
    error(e.client.post(path(form, question) + "/switch-version",
                        headers=e.owner, json={**base, "expected_version_id": original["version_id"],
                                              "jump_rules": []}), 4001)
    error(derive_switch(e, form, question, original["version_id"], original,
                        validation={"required": True}), 4001)


@pytest.mark.parametrize("derive", [False, True])
def test_concurrent_same_request_replays_once(survey_env, derive):
    e = survey_env
    form, question, original = setup(e)
    target = derive_version(e, original, title="目标")
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses = list(pool.map(
            lambda _: (
                derive_switch(e, form, question, original["version_id"], original, title="新派生")
                if derive else switch(e, form, question, original["version_id"], target["version_id"])
            ), range(3),
        ))
    results = [ok(response) for response in responses]
    assert results[0] == results[1] == results[2]
    assert e.db.Question_versions.count_documents({}) == (3 if derive else 2)


def test_concurrent_distinct_switches_have_one_winner_and_no_overwrite(survey_env):
    e = survey_env
    form, question, original = setup(e)
    a = derive_version(e, original, title="A")
    b = derive_version(e, original, key="derive-b", title="B")
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(
            lambda pair: switch(e, form, question, original["version_id"],
                                pair[1]["version_id"], key=pair[0]),
            [("switch-a", a), ("switch-b", b)],
        ))
    assert sorted(r.json()["code"] for r in responses) == [0, 4090]
    winner = next(ok(r) for r in responses if r.json()["code"] == 0)
    assert source(e, form, question).json()["data"]["version_id"] == winner["version_id"]
    assert detail(e, form)["questions"][0]["title"] == winner["title"]


def test_switch_racing_with_publish_keeps_coherent_frozen_form(survey_env):
    e = survey_env
    form, question, original = setup(e)
    target = derive_version(e, original, title="新版")
    with ThreadPoolExecutor(max_workers=2) as pool:
        changing = pool.submit(switch, e, form, question,
                               original["version_id"], target["version_id"])
        publishing = pool.submit(publish, e, form)
        ok(publishing.result())
        result = changing.result()
    assert result.json()["code"] in (0, 4090)
    expected_title = "新版" if result.json()["code"] == 0 else "可复用题"
    assert detail(e, form)["status"] == "published"
    assert detail(e, form)["questions"][0]["title"] == expected_title


def test_concurrent_distinct_derivations_leave_only_winning_new_version(survey_env):
    e = survey_env
    form, question, original = setup(e)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(
            lambda title: derive_switch(
                e, form, question, original["version_id"], original,
                key=f"derive-{title}", title=title,
            ), ["A", "B"],
        ))
    assert sorted(r.json()["code"] for r in responses) == [0, 4090]
    winner = next(ok(r) for r in responses if r.json()["code"] == 0)
    assert e.db.Question_versions.count_documents({}) == 2
    assert e.db.Question_resources.find_one()["last_version_number"] == 2
    assert source(e, form, question).json()["data"]["version_id"] == winner["version_id"]


def test_derive_cross_resource_parent_is_rejected_without_new_version(survey_env):
    e = survey_env
    form, question, original = setup(e)
    foreign = resource(e, key="foreign-resource")
    error(derive_switch(e, form, question, original["version_id"], foreign), 4090)
    assert e.db.Question_versions.count_documents({}) == 2
    assert e.db.Question_operations.count_documents({"request_id": "derive-switch"}) == 0


def test_expired_draft_can_switch_but_existing_invalid_rules_reject_noop(survey_env):
    e = survey_env
    form, question, original = setup(e, "number")
    target = derive_version(e, original, title="新版")
    ok(deadline(e, form, (e.clock.now + timedelta(hours=1)).isoformat()))
    e.clock.now += timedelta(hours=1)
    ok(switch(e, form, question, original["version_id"], target["version_id"]))
    error(publish(e, form), 4090)
    e.db.Questions.update_one({"_id": ObjectId(question["question_id"])}, {"$set": {
        "jump_rules": [{"condition": {"op": "eq", "value": 1},
                        "target": str(ObjectId())}],
    }})
    before = e.db.Question_forms.find_one()
    error(switch(e, form, question, target["version_id"], target["version_id"], key="bad-noop"), 4001)
    assert e.db.Question_forms.find_one() == before
