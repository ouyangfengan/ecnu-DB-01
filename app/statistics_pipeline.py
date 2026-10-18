from functools import partial
from math import isfinite

from app.errors import APIError


def answer_pipeline(form_id, question, ordered=False):
    qid = str(question["_id"])
    stages = [{"$match": {"form_id": form_id, "answers.question_id": qid}}]
    if ordered:
        # 先按提交排序，再展开答案；同一题在一份有效提交中最多出现一次。
        stages.append({"$sort": {"submitted_at": 1, "_id": 1}})
    stages.extend([
        {"$unwind": "$answers"},
        {"$match": {"answers.question_id": qid}},
        {"$project": {"_id": 1, "submitted_at": 1, "value": "$answers.value"}},
    ])
    return stages


def choice_pipeline(form_id, question, multiple):
    option_ids = [option["option_id"] for option in question.get("options", [])]
    allowed = {"$literal": option_ids}
    if multiple:
        predicate = {"$cond": [
            {"$isArray": "$value"},
            {"$and": [
                {"$gt": [{"$size": "$value"}, 0]},
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
    option_counts = ([{"$unwind": "$value"}] if multiple else []) + [
        {"$group": {"_id": "$value", "count": {"$sum": 1}}},
    ]
    return [
        *answer_pipeline(form_id, question),
        {"$match": {"$expr": predicate}},
        {"$facet": {
            "summary": [{"$count": "count"}],
            "options": option_counts,
        }},
    ]


def content_pipeline(form_id, question, numeric, ordered=False):
    stages = answer_pipeline(form_id, question, ordered)
    if numeric:
        stages.extend([
            {"$match": {"$expr": {"$in": [{"$type": "$value"}, ["int", "long", "double"]]}}},
            {"$match": {"$expr": {"$not": [{"$in": [
                {"$convert": {"input": "$value", "to": "string", "onError": "", "onNull": ""}},
                ["NaN", "Infinity", "-Infinity"],
            ]}]}}},
        ])
    else:
        stages.append({"$match": {"$expr": {"$cond": [
            {"$eq": [{"$type": "$value"}, "string"]},
            {"$ne": [{"$trim": {"input": "$value"}}, ""]},
            False,
        ]}}})
    return stages


def choice_statistics(db, form_id, question, session, page, page_size, multiple=False):
    result = next(db.Responses.aggregate(
        choice_pipeline(form_id, question, multiple), session=session
    ))
    counts = {item["_id"]: item["count"] for item in result["options"]}
    return {
        "answer_count": result["summary"][0]["count"] if result["summary"] else 0,
        "options": [
            {"option_id": option["option_id"], "text": option["text"],
             "count": counts.get(option["option_id"], 0)}
            for option in question.get("options", [])
        ],
    }


def content_summary(db, form_id, question, session, numeric):
    group = {"_id": None, "count": {"$sum": 1}}
    if numeric:
        # 先转十进制再求平均，避免合法大浮点数求和溢出；经字符串保留 double 精度。
        group["average"] = {"$avg": {"$toDecimal": {"$toString": "$value"}}}
    result = list(db.Responses.aggregate(
        [*content_pipeline(form_id, question, numeric), {"$group": group}],
        session=session,
    ))
    return result[0] if result else {"count": 0, "average": None}


def content_items(db, form_id, question, session, numeric, page, page_size):
    return list(db.Responses.aggregate([
        *content_pipeline(form_id, question, numeric, ordered=True),
        {"$skip": (page - 1) * page_size},
        {"$limit": page_size},
        {"$project": {"_id": 0, "value": 1}},
    ], session=session))


def content_statistics(db, form_id, question, session, page, page_size, numeric=False):
    summary = content_summary(db, form_id, question, session, numeric)
    result = {
        "answer_count": summary["count"],
        "contents": {
            "items": content_items(db, form_id, question, session, numeric, page, page_size),
            "total": summary["count"], "page": page, "page_size": page_size,
        },
    }
    if numeric:
        average = summary["average"]
        result["average"] = float(average.to_decimal()) if average is not None else None
        if result["average"] is not None and not isfinite(result["average"]):
            raise APIError(5000, "统计结果超出可表示的数值范围", 500)
    return result


STATISTIC_HANDLERS = {
    "single": choice_statistics,
    "multiple": partial(choice_statistics, multiple=True),
    "text": content_statistics,
    "number": partial(content_statistics, numeric=True),
}
