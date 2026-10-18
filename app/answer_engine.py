from math import isfinite

from app.errors import APIError
from app.question_rules import Interval, normalize_config, number, rule_domain
from app.survey_service import question_output


def answer_error(question, message):
    raise APIError(4001, f"第 {question['order']} 题：{message}", 400)


def validate_single(question, value):
    if not isinstance(value, str):
        answer_error(question, "单选答案必须是一个选项 ID")
    if value not in {option["option_id"] for option in question["options"]}:
        answer_error(question, "选项不存在")
    return value


def validate_multiple(question, value):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        answer_error(question, "多选答案必须是选项 ID 列表")
    if len(value) != len(set(value)):
        answer_error(question, "不能重复选择同一选项")
    option_ids = [option["option_id"] for option in question["options"]]
    if not set(value) <= set(option_ids):
        answer_error(question, "选项不存在")
    limits = question["validation"]
    minimum = max(1, limits.get("min_selected", 1))
    maximum = limits.get("max_selected", len(option_ids))
    if len(value) < minimum:
        answer_error(question, f"至少选择 {minimum} 项")
    if len(value) > maximum:
        answer_error(question, f"最多选择 {maximum} 项")
    return [option_id for option_id in option_ids if option_id in value]


def validate_text(question, value):
    if not isinstance(value, str):
        answer_error(question, "文本答案必须为字符串")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        answer_error(question, "文本包含无效的 Unicode 字符")
    limits = question["validation"]
    if len(value) < limits.get("min_length", 0):
        answer_error(question, f"至少填写 {limits['min_length']} 个字符")
    if "max_length" in limits and len(value) > limits["max_length"]:
        answer_error(question, f"最多填写 {limits['max_length']} 个字符")
    return value


def validate_number(question, value):
    try:
        number(value)
    except APIError as error:
        answer_error(question, error.message)
    limits = question["validation"]
    if limits.get("integer_only") and isinstance(value, float) and not value.is_integer():
        answer_error(question, "必须填写整数")
    if "min_value" in limits and value < limits["min_value"]:
        answer_error(question, f"数值不能小于 {limits['min_value']}")
    if "max_value" in limits and value > limits["max_value"]:
        answer_error(question, f"数值不能大于 {limits['max_value']}")
    # 数学意义相同的 1 和 1.0 统一为整数；避免大浮点数转换后超出 BSON int64。
    if isinstance(value, float) and value.is_integer() and -(2**63) <= value < 2**63:
        return int(value)
    return value


ANSWER_VALIDATORS = {
    "single": validate_single,
    "multiple": validate_multiple,
    "text": validate_text,
    "number": validate_number,
}


def validate_answer(question, value):
    normalize_config(question)
    kind = question["type"]
    empty = value is None
    if kind in ("single", "text") and isinstance(value, str) and not value.strip():
        empty = True
    if kind == "multiple" and isinstance(value, list) and not value:
        empty = True
    if empty:
        if question["validation"]["required"]:
            answer_error(question, "该题为必答题")
        return None
    return ANSWER_VALIDATORS[kind](question, value)


def matches(question, value, condition):
    if value is None:
        return False
    domain = rule_domain(question, condition)
    if isinstance(domain, Interval):
        return (
            (value > domain.lower or (domain.include_lower and value == domain.lower))
            and (value < domain.upper or (domain.include_upper and value == domain.upper))
        )
    if isinstance(domain, frozenset):
        return frozenset(value) == domain
    return value == domain


def replay_answers(questions, answers, final=False):
    questions = sorted(questions, key=lambda question: question["order"])
    if not questions:
        raise APIError(4090, "问卷没有可填写的题目", 409)
    positions = {str(question["_id"]): index for index, question in enumerate(questions)}
    supplied = {}
    for item in answers:
        qid = item["question_id"]
        if qid not in positions:
            raise APIError(4001, "答案包含不属于该问卷的题目", 400)
        if qid in supplied:
            raise APIError(4001, "同一道题不能重复提供答案", 400)
        supplied[qid] = item.get("value")

    accepted, consumed = [], set()
    index = 0
    while index < len(questions):
        question = questions[index]
        qid = str(question["_id"])
        # 进度接口需要显式的 null 来跳过选答题；最终提交允许省略选答题。
        if qid not in supplied and not final:
            break
        value = validate_answer(question, supplied.get(qid))
        accepted.append({"question_id": qid, "value": value})
        consumed.add(qid)
        hits = [
            rule for rule in question.get("jump_rules", [])
            if matches(question, value, rule["condition"])
        ]
        if len(hits) > 1:
            raise APIError(5000, "问卷跳转配置冲突，请联系创建者", 500)
        if not hits:
            index += 1
            continue
        target = hits[0]["target"]
        if target == "end":
            index = len(questions)
        elif target not in positions or positions[target] <= index:
            raise APIError(5000, "问卷跳转目标无效，请联系创建者", 500)
        else:
            index = positions[target]

    complete = index == len(questions)
    return {
        "answers": accepted,
        "discarded_question_ids": sorted(supplied.keys() - consumed),
        "next_question": None if complete else question_output(questions[index]),
        "complete": complete,
    }


def canonical_answers(answers):
    result = []
    seen = set()
    for item in answers:
        qid, value = item["question_id"], item.get("value")
        if qid in seen:
            raise APIError(4001, "同一道题不能重复提供答案", 400)
        seen.add(qid)
        if isinstance(value, list) and all(isinstance(option, str) for option in value):
            value = sorted(value)
        elif isinstance(value, float) and isfinite(value) and value.is_integer():
            if -(2**63) <= value < 2**63:
                value = int(value)
        result.append({"question_id": qid, "value": value})
    return sorted(result, key=lambda item: item["question_id"])
