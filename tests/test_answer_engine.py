from copy import deepcopy

import pytest
from bson import ObjectId

from app.answer_engine import replay_answers, validate_answer
from app.errors import APIError
from app.filling_service import request_fingerprint


def question(kind="text", order=1, **limits):
    return {
        "_id": ObjectId(), "order": order, "type": kind, "title": f"题目{order}",
        "validation": limits, "jump_rules": [],
        "options": [{"option_id": option, "text": option} for option in ("a", "b", "c")]
        if kind in ("single", "multiple") else [],
    }


def answer(q, value):
    return {"question_id": str(q["_id"]), "value": value}


@pytest.mark.parametrize("kind,value", [
    ("single", "a"), ("multiple", ["b", "a"]), ("text", " 保留空格 "), ("number", 0),
])
def test_valid_answers(kind, value):
    result = validate_answer(question(kind, required=True), value)
    assert result == (["a", "b"] if kind == "multiple" else value)


@pytest.mark.parametrize("kind,empty", [
    ("single", None), ("single", ""), ("multiple", []), ("multiple", None),
    ("text", ""), ("text", " \t\n"), ("number", None),
])
def test_required_and_optional_empty_answers(kind, empty):
    assert validate_answer(question(kind), empty) is None
    with pytest.raises(APIError) as caught:
        validate_answer(question(kind, order=2, required=True), empty)
    assert caught.value.code == 4001
    assert caught.value.message == "第 2 题：该题为必答题"


@pytest.mark.parametrize("kind,value", [
    ("single", ["a"]), ("single", "unknown"), ("multiple", "a"),
    ("multiple", ["a", "a"]), ("multiple", ["unknown"]), ("multiple", [True]),
    ("text", 123), ("text", "\ud800"),
    ("number", True), ("number", False), ("number", "12"),
    ("number", ""), ("number", []), ("number", float("nan")),
    ("number", float("inf")), ("number", 2**63),
])
def test_invalid_answer_types_and_values(kind, value):
    with pytest.raises(APIError) as caught:
        validate_answer(question(kind), value)
    assert caught.value.code == 4001
    assert caught.value.message.startswith("第 1 题：")


def test_multiple_min_max_exact_and_optional_omission():
    q = question("multiple", required=True)
    assert validate_answer(q, ["a"]) == ["a"]
    with pytest.raises(APIError):
        validate_answer(q, [])
    q = question("multiple", min_selected=2, max_selected=2)
    assert validate_answer(q, []) is None
    for value in (["a"], ["a", "b", "c"]):
        with pytest.raises(APIError):
            validate_answer(q, value)
    assert validate_answer(q, ["b", "a"]) == ["a", "b"]


def test_text_limits_count_characters_without_trimming_nonempty_text():
    q = question("text", min_length=2, max_length=3)
    assert validate_answer(q, "中文") == "中文"
    assert validate_answer(q, " 甲 ") == " 甲 "
    assert validate_answer(q, "   ") is None
    for value in ("甲", "中文四字"):
        with pytest.raises(APIError):
            validate_answer(q, value)


def test_numeric_inclusive_bounds_and_mathematical_integers():
    q = question("number", min_value=0, max_value=10, integer_only=True)
    assert validate_answer(q, 0) == 0
    assert validate_answer(q, 10.0) == 10
    assert type(validate_answer(q, 10.0)) is int
    for value in (-1, 11, 1.1):
        with pytest.raises(APIError):
            validate_answer(q, value)


def test_progress_requires_explicit_skip_and_final_can_omit_optional_answer():
    first, second = question(), question(order=2, required=True)
    result = replay_answers([first, second], [])
    assert result["next_question"]["question_id"] == str(first["_id"])
    assert result["complete"] is False
    result = replay_answers([first, second], [answer(first, None)])
    assert result["next_question"]["question_id"] == str(second["_id"])
    with pytest.raises(APIError):
        replay_answers([first, second], [], final=True)
    result = replay_answers([first, second], [answer(second, "已答")], final=True)
    assert result["complete"] is True
    assert result["answers"] == [answer(first, None), answer(second, "已答")]


def test_forward_jump_skips_required_questions_and_discards_old_invalid_answers():
    first = question("single", required=True)
    second, third, fourth = [question(order=n, required=True) for n in (2, 3, 4)]
    first["jump_rules"] = [
        {"condition": {"op": "eq", "value": "a"}, "target": str(fourth["_id"])}
    ]
    answers = [
        answer(first, "a"), answer(second, {"invalid": "stale"}),
        answer(third, None), answer(fourth, "有效答案"),
    ]
    result = replay_answers([first, second, third, fourth], answers, final=True)
    assert result["answers"] == [answer(first, "a"), answer(fourth, "有效答案")]
    assert set(result["discarded_question_ids"]) == {str(second["_id"]), str(third["_id"])}
    assert result["complete"] is True
    # 改回不跳转后，第 2 题重新进入路径，旧的非法答案不能继续使用。
    answers[0] = answer(first, "b")
    with pytest.raises(APIError):
        replay_answers([first, second, third, fourth], answers, final=True)


def test_multiple_jump_is_exact_set_matching_not_contains():
    first, second = question("multiple"), question(order=2, required=True)
    first["jump_rules"] = [{"condition": {"op": "exact", "value": ["a", "b"]}, "target": "end"}]
    assert replay_answers([first, second], [answer(first, ["b", "a"])])["complete"]
    for value in (["a"], ["a", "b", "c"], []):
        result = replay_answers([first, second], [answer(first, value)])
        assert result["next_question"]["question_id"] == str(second["_id"])


@pytest.mark.parametrize("condition,hit,miss", [
    ({"op": "eq", "value": 3}, 3, 4),
    ({"op": "lt", "value": 3}, 2, 3),
    ({"op": "lte", "value": 3}, 3, 4),
    ({"op": "gt", "value": 3}, 4, 3),
    ({"op": "gte", "value": 3}, 3, 2),
    ({"op": "between", "lower": 0, "upper": 3, "include_upper": False}, 0, 3),
    ({"op": "between", "lower": 0, "upper": 3, "include_lower": False}, 3, 0),
])
def test_numeric_jump_operators(condition, hit, miss):
    first, second = question("number"), question(order=2)
    first["jump_rules"] = [{"condition": condition, "target": "end"}]
    assert replay_answers([first, second], [answer(first, hit)])["complete"]
    assert not replay_answers([first, second], [answer(first, miss)])["complete"]
    assert not replay_answers([first, second], [answer(first, None)])["complete"]


def test_partial_path_does_not_accept_answers_past_an_unanswered_question():
    first, second = question(required=True), question(order=2)
    result = replay_answers([first, second], [answer(second, "过早提供")])
    assert result["answers"] == []
    assert result["discarded_question_ids"] == [str(second["_id"])]
    assert result["next_question"]["question_id"] == str(first["_id"])


def test_duplicates_and_foreign_questions_are_rejected():
    q = question()
    for answers in ([answer(q, "a"), answer(q, "b")], [answer(question(), "外部题目")]):
        with pytest.raises(APIError):
            replay_answers([q], answers, final=True)


def test_invalid_runtime_jump_config_fails_closed_instead_of_looping():
    first = question("single")
    for target in (str(first["_id"]), str(ObjectId())):
        first["jump_rules"] = [{"condition": {"op": "eq", "value": "a"}, "target": target}]
        with pytest.raises(APIError) as caught:
            replay_answers([first], [answer(first, "a")], final=True)
        assert caught.value.code == 5000
    first["jump_rules"] = [{"condition": {"op": "eq", "value": "a"}, "target": "end"}] * 2
    with pytest.raises(APIError) as caught:
        replay_answers([first], [answer(first, "a")], final=True)
    assert caught.value.code == 5000


def test_request_hash_is_order_independent_but_preserves_text_content():
    one, two, three = question("multiple"), question("number", order=2), question(order=3)
    answers = [answer(one, ["a", "b"]), answer(two, 1.0), answer(three, "内容")]
    equivalent = [answer(three, "内容"), answer(two, 1), answer(one, ["b", "a"])]
    assert request_fingerprint(answers) == request_fingerprint(equivalent)
    changed = deepcopy(answers)
    changed[2]["value"] = " 内容 "
    assert request_fingerprint(answers) != request_fingerprint(changed)
