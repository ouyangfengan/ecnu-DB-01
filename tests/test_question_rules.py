from copy import deepcopy

import pytest
from bson import ObjectId

from app.errors import APIError
from app.question_rules import validate_form_questions


def question(kind="number", validation=None, rules=None):
    return {
        "_id": ObjectId(), "form_id": ObjectId(), "order": 1, "title": "题目",
        "type": kind,
        "options": [{"option_id": v, "text": v} for v in ("a", "b", "c")]
        if kind in ("single", "multiple") else [],
        "validation": validation or {},
        "jump_rules": rules or [],
    }


def rule(op, value=None, **kwargs):
    condition = {"op": op, **kwargs}
    if op != "between":
        condition["value"] = value
    return {"condition": condition, "target": "end"}


@pytest.mark.parametrize("op,value", [("eq", 2), ("lt", 2), ("lte", 2), ("gt", 2), ("gte", 2)])
def test_numeric_operators(op, value):
    validate_form_questions([question(rules=[rule(op, value)])])


def test_overlapping_numeric_rules_rejected_even_same_target():
    q = question(rules=[rule("gte", 2), rule("lte", 2)])
    with pytest.raises(APIError, match=""):
        validate_form_questions([q])


def test_open_boundary_rules_are_mutually_exclusive():
    validate_form_questions([question(rules=[rule("lt", 2), rule("gte", 2)])])


def test_integer_overlap_is_computed_only_on_valid_integer_answers():
    rules = [
        rule("between", lower=0, upper=1.5),
        rule("between", lower=1.2, upper=3),
    ]
    validate_form_questions([question(validation={"integer_only": True}, rules=rules)])
    with pytest.raises(APIError):
        validate_form_questions([question(rules=rules)])


def test_overlap_outside_numeric_validation_range_does_not_count():
    validate_form_questions([question(
        validation={"min_value": 0},
        rules=[rule("lt", 0.5), rule("gte", 0.5)],
    )])
    with pytest.raises(APIError):
        validate_form_questions([question(
            validation={"min_value": 0}, rules=[rule("lt", -1)]
        )])


@pytest.mark.parametrize("validation", [
    {"min_value": 10, "max_value": 1},
    {"integer_only": True, "min_value": 0.1, "max_value": 0.9},
    {"min_value": True}, {"max_value": "1"}, {"integer_only": 1},
    {"min_value": float("nan")}, {"max_value": float("inf")},
    {"min_value": 2**64}, {"min_selected": 1}, {"required": "true"},
])
def test_invalid_numeric_configs(validation):
    with pytest.raises(APIError):
        validate_form_questions([question(validation=validation)])


@pytest.mark.parametrize("condition", [
    {"op": "between", "lower": 1, "upper": 1, "include_lower": False},
    {"op": "between", "lower": 2, "upper": 1},
    {"op": "between", "lower": 1},
    {"op": "between", "lower": 0, "upper": 1, "include_upper": "false"},
    {"op": "eq", "value": False},
    {"op": "eq", "value": 1, "lower": 0},
    {"op": "unknown", "value": 1},
    {"op": ["eq"], "value": 1},
])
def test_invalid_numeric_conditions(condition):
    with pytest.raises(APIError):
        validate_form_questions([question(rules=[{"condition": condition, "target": "end"}])])


def test_required_multiple_without_minimum_is_valid_but_max_zero_is_not():
    q = question("multiple", {"required": True})
    validate_form_questions([q])
    assert q["validation"] == {"required": True}
    with pytest.raises(APIError):
        validate_form_questions([question("multiple", {"required": True, "max_selected": 0})])


@pytest.mark.parametrize("validation", [
    {"min_selected": -1}, {"min_selected": True}, {"max_selected": 4},
    {"min_selected": 3, "max_selected": 2}, {"min_selected": 1.5},
])
def test_invalid_multiple_limits(validation):
    with pytest.raises(APIError):
        validate_form_questions([question("multiple", validation)])


def test_multiple_rules_compare_sets_not_order_or_shared_options():
    validate_form_questions([question("multiple", rules=[
        rule("exact", ["a", "b"]), rule("exact", ["a", "c"]),
    ])])
    with pytest.raises(APIError):
        validate_form_questions([question("multiple", rules=[
            rule("exact", ["a", "b"]), rule("exact", ["b", "a"]),
        ])])


@pytest.mark.parametrize("value", [[], ["a", "a"], ["missing"], ["a", 1], "a"])
def test_invalid_multiple_conditions(value):
    with pytest.raises(APIError):
        validate_form_questions([question("multiple", rules=[rule("exact", value)])])


def test_multiple_condition_must_meet_selection_limits():
    with pytest.raises(APIError):
        validate_form_questions([question(
            "multiple", {"min_selected": 2}, [rule("exact", ["a"])]
        )])


def test_single_rules_and_text_rules():
    validate_form_questions([question("single", rules=[rule("eq", "a"), rule("eq", "b")])])
    for q in [
        question("single", rules=[rule("eq", "a"), rule("eq", "a")]),
        question("single", rules=[rule("eq", "unknown")]),
        question("text", rules=[rule("eq", "a")]),
        question("text", validation={"min_length": 3, "max_length": 1}),
    ]:
        with pytest.raises(APIError):
            validate_form_questions([q])


def test_only_existing_forward_targets_are_allowed():
    first, second = question(), question("text")
    second["order"] = 2
    first["jump_rules"] = [{"condition": {"op": "eq", "value": 1}, "target": str(second["_id"])}]
    validate_form_questions([first, second])
    for target in (str(first["_id"]), str(ObjectId())):
        candidate = deepcopy(first)
        candidate["jump_rules"][0]["target"] = target
        with pytest.raises(APIError):
            validate_form_questions([candidate, second])
