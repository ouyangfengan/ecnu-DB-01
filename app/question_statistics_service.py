import logging
from decimal import Decimal
from math import isfinite

from bson.decimal128 import Decimal128

from app.errors import APIError
from app.question_resource_service import (
    QuestionResourceService, canonical_question_content,
)
from app.survey_service import object_id


logger = logging.getLogger(__name__)

NUMERIC_TYPES = ["int", "long", "double", "decimal"]
NON_FINITE_TEXT = ["NaN", "Infinity", "-Infinity"]


def decimal_text(value):
    # 定点输出规范化十进制：无指数、无多余尾零，负零归零。
    if isinstance(value, Decimal128):
        value = value.to_decimal()
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def answer_pipeline(form_ids, pairs):
    qids = sorted({qid for _, qid in pairs})
    keys = sorted(f"{form_id}|{qid}" for form_id, qid in pairs)
    return [
        {"$match": {
            "form_id": {"$in": sorted(form_ids)},
            "answers.question_id": {"$in": qids},
        }},
        {"$unwind": "$answers"},
        {"$match": {"answers.question_id": {"$in": qids}}},
        # 问卷与卷内题必须成对归属，错配答案不计入。
        {"$match": {"$expr": {"$in": [
            {"$concat": [{"$toString": "$form_id"}, "|", "$answers.question_id"]},
            keys,
        ]}}},
        # 同一答卷同一卷内题出现多条答案时整组排除，内容是否相同都不计。
        {"$group": {
            "_id": {"response_id": "$_id", "question_id": "$answers.question_id"},
            "count": {"$sum": 1},
            "doc": {"$first": {
                "response_id": "$_id", "submitted_at": "$submitted_at",
                "value": "$answers.value",
            }},
        }},
        {"$match": {"count": 1}},
        {"$replaceRoot": {"newRoot": "$doc"}},
    ]


def choice_pipeline(source, pipeline, multiple):
    option_ids = [option["option_id"] for option in source["options"]]
    allowed = {"$literal": option_ids}
    if multiple:
        limits = source.get("validation", {})
        minimum = max(1, limits.get("min_selected", 1))
        maximum = limits.get("max_selected", len(option_ids))
        predicate = {"$cond": [
            {"$isArray": "$value"},
            {"$and": [
                {"$gte": [{"$size": "$value"}, minimum]},
                {"$lte": [{"$size": "$value"}, maximum]},
                {"$setIsSubset": ["$value", allowed]},
                {"$eq": [{"$size": "$value"}, {"$size": {"$setUnion": ["$value", []]}}]},
            ]},
            False,
        ]}
    else:
        predicate = {"$and": [
            {"$eq": [{"$type": "$value"}, "string"]},
            {"$in": ["$value", allowed]},
        ]}
    counts = ([{"$unwind": "$value"}] if multiple else []) + [
        {"$group": {"_id": "$value", "count": {"$sum": 1}}},
    ]
    return [
        *pipeline,
        {"$match": {"$expr": predicate}},
        {"$facet": {"summary": [{"$count": "count"}], "options": counts}},
    ]


def text_pipeline(source, pipeline, page, page_size):
    limits = source.get("validation", {})
    predicate = [
        {"$eq": [{"$type": "$value"}, "string"]},
        {"$ne": [{"$trim": {"input": "$value"}}, ""]},
        {"$gte": [{"$strLenCP": "$value"}, limits.get("min_length", 0)]},
    ]
    if "max_length" in limits:
        predicate.append({"$lte": [{"$strLenCP": "$value"}, limits["max_length"]]})
    return [
        *pipeline,
        {"$match": {"$expr": {"$and": predicate}}},
        {"$sort": {"submitted_at": 1, "response_id": 1}},
        {"$facet": {
            "summary": [{"$count": "count"}],
            "items": [
                {"$skip": (page - 1) * page_size}, {"$limit": page_size},
                {"$project": {"_id": 0, "value": 1}},
            ],
        }},
    ]


def number_pipeline(source, pipeline, page, page_size):
    limits = source.get("validation", {})
    stages = [*pipeline, {"$match": {"$expr": {"$and": [
        {"$in": [{"$type": "$value"}, NUMERIC_TYPES]},
        # 有限性判断沿用第一阶段写法，避免另写一套判定。
        {"$not": [{"$in": [
            {"$convert": {"input": "$value", "to": "string", "onError": "", "onNull": ""}},
            NON_FINITE_TEXT,
        ]}]},
    ]}}}]
    if limits.get("integer_only"):
        stages.append({"$match": {"$expr": {"$eq": [{"$mod": ["$value", 1]}, 0]}}})
    if "min_value" in limits:
        stages.append({"$match": {"$expr": {"$gte": ["$value", limits["min_value"]]}}})
    if "max_value" in limits:
        stages.append({"$match": {"$expr": {"$lte": ["$value", limits["max_value"]]}}})
    # 等值归一：20 与 20.0 合并，负零归零；排序仍按数值进行。
    stages.append({"$set": {"normalized": {"$cond": [
        {"$eq": ["$value", 0]},
        {"$toDecimal": 0},
        {"$toDecimal": {"$toString": "$value"}},
    ]}}})
    stages.append({"$facet": {
        "summary": [{"$group": {
            "_id": None, "answer_count": {"$sum": 1},
            "min_value": {"$min": "$normalized"},
            "max_value": {"$max": "$normalized"},
            "average": {"$avg": "$normalized"},
        }}],
        "values": [
            {"$group": {"_id": "$normalized", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$skip": (page - 1) * page_size}, {"$limit": page_size},
            {"$project": {"_id": 0, "value": "$_id", "count": 1}},
        ],
        "distinct": [{"$group": {"_id": "$normalized"}}, {"$count": "total"}],
    }})
    return stages


class QuestionStatisticsService(QuestionResourceService):
    def statistics(self, resource_id, version_id, user_id, page, page_size):
        resource_id, version_id = object_id(resource_id), object_id(version_id)

        def callback(session):
            return self.collect(
                resource_id, version_id, user_id, page, page_size, session
            )

        return self.transaction(callback)

    def collect(self, resource_id, version_id, user_id, page, page_size, session):
        resource = self.db.Question_resources.find_one(
            {"_id": resource_id}, {"_id": 1, "owner_id": 1}, session=session
        )
        if resource is None:
            raise APIError(4040, "题目资源不存在", 404)
        version = self.db.Question_versions.find_one(
            {"_id": version_id, "resource_id": resource_id}, session=session
        )
        if version is None:
            raise APIError(4040, "题目版本不存在", 404)
        owner = resource["owner_id"] == user_id
        authorized = owner or self.db.Question_shares.find_one({
            "resource_id": resource_id, "version_id": version_id,
            "recipient_id": user_id, "status": "active",
        }, {"_id": 1}, session=session) is not None

        try:
            target = canonical_question_content(version["content"])
        except APIError:
            raise APIError(5000, "题目版本内容无效", 500) from None
        pairs, form_ids, copy = self.qualifying_links(
            resource_id, version_id, user_id, target, session
        )
        if not authorized and not form_ids:
            raise APIError(4030, "没有有效授权或本人既有引用", 403)

        # 展示与规则一律取自本人副本；无可纳入副本时才使用已授权可读的版本内容。
        source = copy if copy is not None else version["content"]
        result = {
            "resource_id": str(resource_id), "version_id": str(version_id),
            "version_number": version["version_number"],
            "type": source["type"], "title": source["title"],
            "survey_count": len(form_ids),
        }
        pipeline = answer_pipeline(form_ids, pairs)
        kind = source["type"]
        if kind in ("single", "multiple"):
            result.update(self.choice_result(
                source, pipeline, kind == "multiple", session
            ))
        elif kind == "text":
            result.update(self.text_result(source, pipeline, page, page_size, session))
        else:
            result.update(self.number_result(source, pipeline, page, page_size, session))
        return result

    def qualifying_links(self, resource_id, version_id, user_id, target, session):
        pairs, form_ids, copies = [], set(), []
        links = self.db.Question_links.find(
            {"resource_id": resource_id, "version_id": version_id}, session=session
        )
        for link in links:
            form = self.db.Question_forms.find_one(
                {"_id": link["form_id"]}, {"_id": 1, "owner_id": 1}, session=session
            )
            if form is None or form["owner_id"] != user_id:
                continue
            question = self.db.Questions.find_one(
                {"_id": link["question_id"], "form_id": link["form_id"]}, session=session
            )
            if question is None or not self.consistent(question, target):
                # 异常关联只做纳入判断，响应结构与正常结果完全一致。
                logger.warning("跨卷统计排除异常关联 %s", link["_id"])
                continue
            form_ids.add(link["form_id"])
            pairs.append((str(link["form_id"]), str(link["question_id"])))
            copies.append(question)
        copies.sort(key=lambda item: str(item["_id"]))
        return pairs, form_ids, (copies[0] if copies else None)

    @staticmethod
    def consistent(question, target):
        try:
            return canonical_question_content(question) == target
        except APIError:
            return False

    def choice_result(self, source, pipeline, multiple, session):
        result = next(self.db.Responses.aggregate(
            choice_pipeline(source, pipeline, multiple), session=session
        ))
        total = result["summary"][0]["count"] if result["summary"] else 0
        counts = {item["_id"]: item["count"] for item in result["options"]}
        return {
            "answer_count": total,
            "options": [
                {"option_id": option["option_id"], "text": option["text"],
                 "count": counts.get(option["option_id"], 0),
                 "ratio": counts.get(option["option_id"], 0) / total if total else 0}
                for option in source["options"]
            ],
        }

    def text_result(self, source, pipeline, page, page_size, session):
        result = next(self.db.Responses.aggregate(
            text_pipeline(source, pipeline, page, page_size), session=session
        ))
        total = result["summary"][0]["count"] if result["summary"] else 0
        return {
            "answer_count": total,
            "contents": {"items": result["items"], "total": total,
                         "page": page, "page_size": page_size},
        }

    def number_result(self, source, pipeline, page, page_size, session):
        result = next(self.db.Responses.aggregate(
            number_pipeline(source, pipeline, page, page_size), session=session
        ))
        summary = result["summary"][0] if result["summary"] else {}
        total = summary.get("answer_count", 0)
        distinct = result["distinct"][0]["total"] if result["distinct"] else 0
        average = summary.get("average")
        if average is not None:
            # 平均值是派生量，保留浮点近似，不做四舍五入。
            average = float(average.to_decimal())
            if not isfinite(average):
                raise APIError(5000, "统计结果超出可表示的数值范围", 500)
        return {
            "answer_count": total,
            "min_value": decimal_text(summary["min_value"]) if total else None,
            "max_value": decimal_text(summary["max_value"]) if total else None,
            "average": average,
            "values": {
                "items": [
                    {"value": decimal_text(row["value"]), "count": row["count"]}
                    for row in result["values"]
                ],
                "total": distinct, "page": page, "page_size": page_size,
            },
        }
