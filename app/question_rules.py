from dataclasses import dataclass
from itertools import combinations
from math import ceil, floor, inf, isfinite

from app.errors import APIError


# 注册表描述题型能力，具体限制和跳转条件保存在每道题的 MongoDB 文档中。
TYPE_SPECS = {
    "single": {"options": True, "limits": set(), "ops": {"eq"}},
    "multiple": {
        "options": True, "limits": {"min_selected", "max_selected"}, "ops": {"exact"},
    },
    "text": {"options": False, "limits": {"min_length", "max_length"}, "ops": set()},
    "number": {
        "options": False, "limits": {"min_value", "max_value", "integer_only"},
        "ops": {"eq", "lt", "lte", "gt", "gte", "between"},
    },
}


def reject(message):
    raise APIError(4001, message, 400)


def number(value):
    if type(value) not in (int, float):
        reject("数字限制和跳转阈值必须是有限数字")
    if isinstance(value, int) and not -(2**63) <= value < 2**63:
        reject("整数超出 MongoDB 的 64 位存储范围")
    if not isfinite(value):
        reject("数字限制和跳转阈值必须是有限数字")
    return value


@dataclass(frozen=True)
class Interval:
    lower: int | float = -inf
    upper: int | float = inf
    include_lower: bool = True
    include_upper: bool = True

    def intersect(self, other):
        lo, hi = max(self.lower, other.lower), min(self.upper, other.upper)
        return Interval(
            lo, hi,
            (lo != self.lower or self.include_lower)
            and (lo != other.lower or other.include_lower),
            (hi != self.upper or self.include_upper)
            and (hi != other.upper or other.include_upper),
        )

    def has_value(self, integer_only=False):
        if self.lower > self.upper:
            return False
        if integer_only:
            lo = self.lower
            hi = self.upper
            if isfinite(lo):
                lo = ceil(lo) if self.include_lower else floor(lo) + 1
            if isfinite(hi):
                hi = floor(hi) if self.include_upper else ceil(hi) - 1
            return lo <= hi
        return self.lower < self.upper or (self.include_lower and self.include_upper)


def numeric_condition(condition):
    op = condition["op"]
    if op == "between":
        allowed = {"op", "lower", "upper", "include_lower", "include_upper"}
        if set(condition) - allowed or not {"lower", "upper"} <= condition.keys():
            reject("区间跳转必须提供 lower、upper，且不能包含其他比较参数")
        lo, hi = number(condition["lower"]), number(condition["upper"])
        lower_closed = condition.get("include_lower", True)
        upper_closed = condition.get("include_upper", True)
        if type(lower_closed) is not bool or type(upper_closed) is not bool:
            reject("区间边界包含标记必须为布尔值")
        result = Interval(lo, hi, lower_closed, upper_closed)
    else:
        if set(condition) != {"op", "value"}:
            reject("数字比较必须且只能提供 op 和 value")
        value = number(condition["value"])
        factories = {
            "eq": lambda: Interval(value, value),
            "lt": lambda: Interval(upper=value, include_upper=False),
            "lte": lambda: Interval(upper=value),
            "gt": lambda: Interval(lower=value, include_lower=False),
            "gte": lambda: Interval(lower=value),
        }
        result = factories[op]()
    if not result.has_value():
        reject("数字跳转区间不能为空")
    return result


def normalize_config(question):
    spec = TYPE_SPECS.get(question["type"])
    if spec is None:
        reject("不支持的题型")
    options = question.get("options", [])
    if spec["options"]:
        if len(options) < 2:
            reject("选择题至少需要两个选项")
        ids = [option["option_id"] for option in options]
        if len(ids) != len(set(ids)):
            reject("选项 ID 不能重复")
    elif options:
        reject("文本题和数字题不能配置选项")

    v = question.get("validation", {}).copy()
    if set(v) - ({"required"} | spec["limits"]):
        reject("校验配置包含当前题型不支持的字段")
    v.setdefault("required", False)
    if type(v["required"]) is not bool:
        reject("required 必须为布尔值")
    for key in list(v):
        if key not in {"required", "integer_only"} and v[key] is None:
            del v[key]
    for key in ("min_selected", "max_selected", "min_length", "max_length"):
        if key in v and (type(v[key]) is not int or v[key] < 0):
            reject("选择数量和文本长度限制必须为非负整数")
    for lower, upper in (
        ("min_selected", "max_selected"), ("min_length", "max_length"),
        ("min_value", "max_value"),
    ):
        if lower in v and upper in v:
            if lower == "min_value":
                number(v[lower])
                number(v[upper])
            if v[lower] > v[upper]:
                reject("最小限制不能大于最大限制")
    if question["type"] == "multiple":
        lo, hi = max(1, v.get("min_selected", 1)), v.get("max_selected", len(options))
        if any(v[k] > len(options) for k in ("min_selected", "max_selected") if k in v):
            reject("多选数量限制不能超过选项数")
        if lo > hi:
            reject("多选配置必须允许至少一个合法的非空答案")
    if question["type"] == "number":
        v.setdefault("integer_only", False)
        if type(v["integer_only"]) is not bool:
            reject("integer_only 必须为布尔值")
        for key in ("min_value", "max_value"):
            if key in v:
                number(v[key])
        domain = Interval(v.get("min_value", -inf), v.get("max_value", inf))
        if not domain.has_value(v["integer_only"]):
            reject("数字范围内不存在符合整数限制的答案")
    question["validation"] = v


def rule_domain(question, condition):
    op = condition.get("op")
    if not isinstance(op, str) or op not in TYPE_SPECS[question["type"]]["ops"]:
        reject("当前题型不支持此跳转操作符")
    if question["type"] == "number":
        v = question["validation"]
        domain = numeric_condition(condition).intersect(
            Interval(v.get("min_value", -inf), v.get("max_value", inf))
        )
        if not domain.has_value(v["integer_only"]):
            reject("跳转条件在该题合法答案范围内不可能满足")
        return domain
    if set(condition) != {"op", "value"}:
        reject("选项跳转必须且只能提供 op 和 value")
    value = condition["value"]
    ids = {o["option_id"] for o in question["options"]}
    if question["type"] == "single":
        if not isinstance(value, str) or value not in ids:
            reject("跳转条件引用了不存在的选项")
        return value
    if (
        not isinstance(value, list) or not value
        or any(not isinstance(item, str) for item in value)
    ):
        reject("多选跳转的 value 必须是非空选项 ID 列表")
    if len(value) != len(set(value)) or not set(value) <= ids:
        reject("多选跳转选项不能重复，且必须属于当前题目")
    v = question["validation"]
    if not max(1, v.get("min_selected", 1)) <= len(value) <= v.get("max_selected", len(ids)):
        reject("多选跳转条件不满足该题的选择数量限制")
    return frozenset(value)


def validate_form_questions(questions):
    by_id = {str(q["_id"]): q for q in questions}
    for question in questions:
        normalize_config(question)
        domains = []
        for rule in question.get("jump_rules", []):
            target = rule["target"]
            if target != "end":
                destination = by_id.get(target)
                if destination is None:
                    reject("跳转目标不存在或不属于当前问卷")
                if destination["order"] <= question["order"]:
                    reject("只能跳转到后续题目或 end")
            domains.append(rule_domain(question, rule["condition"]))
        for left, right in combinations(domains, 2):
            if isinstance(left, Interval):
                conflict = left.intersect(right).has_value(
                    question["validation"]["integer_only"]
                )
            else:
                conflict = left == right
            if conflict:
                reject("同一题的跳转规则必须互斥")
