from app.errors import APIError
from app.question_resource_service import QuestionResourceService
from app.survey_service import effective_status, object_id


def valid_links(scope, user_id=None, details=False):
    form_match = {"$expr": {"$eq": ["$_id", "$$form_id"]}}
    if user_id is not None:
        form_match["owner_id"] = user_id
    form_fields = {"_id": 1, "owner_id": 1}
    question_fields = {"_id": 1, "form_id": 1}
    if details:
        form_fields.update(title=1, status=1, deadline=1, created_at=1)
        question_fields["order"] = 1
    return [
        {"$match": scope},
        {"$project": {"_id": 0, "resource_id": 1, "version_id": 1,
                      "form_id": 1, "question_id": 1}},
        {"$lookup": {
            "from": "Question_versions",
            "let": {"version_id": "$version_id", "resource_id": "$resource_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$_id", "$$version_id"]},
                    {"$eq": ["$resource_id", "$$resource_id"]},
                ]}}},
                {"$project": {"_id": 1, "resource_id": 1}},
            ],
            "as": "version",
        }},
        {"$unwind": "$version"},
        {"$project": {"version": 0}},
        {"$lookup": {
            "from": "Question_forms", "let": {"form_id": "$form_id"},
            "pipeline": [
                {"$match": form_match}, {"$project": form_fields},
            ],
            "as": "form",
        }},
        {"$unwind": "$form"},
        {"$lookup": {
            "from": "Questions",
            "let": {"question_id": "$question_id", "form_id": "$form_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [
                    {"$eq": ["$_id", "$$question_id"]},
                    {"$eq": ["$form_id", "$$form_id"]},
                ]}}},
                {"$project": question_fields},
            ],
            "as": "question",
        }},
        {"$unwind": "$question"},
    ]


def own_pipeline(scope, user_id, page, page_size):
    return [
        *valid_links(scope, user_id, details=True),
        {"$sort": {"form_id": 1, "question.order": 1, "question._id": 1}},
        {"$group": {
            "_id": "$form_id", "form": {"$first": "$form"},
            "questions": {"$push": {
                "question_id": "$question._id", "version_id": "$version_id",
            }},
        }},
        {"$set": {
            "sort_created_at": {"$ifNull": ["$form.created_at", {"$toDate": "$_id"}]},
        }},
        # 计数分支不受 skip/limit 影响，空结果和越界页分别处理。
        {"$facet": {
            "count": [{"$count": "total"}],
            "items": [
                {"$sort": {"sort_created_at": -1, "_id": -1}},
                {"$skip": (page - 1) * page_size}, {"$limit": page_size},
                {"$project": {"_id": 0, "form": 1, "questions": 1}},
            ],
        }},
    ]


def summary_pipeline(scope, user_id):
    return [
        *valid_links(scope),
        {"$group": {
            "_id": "$form_id",
            "is_own": {"$first": {"$eq": ["$form.owner_id", user_id]}},
        }},
        {"$group": {
            "_id": None, "survey_count": {"$sum": 1},
            "own_survey_count": {"$sum": {"$cond": ["$is_own", 1, 0]}},
            "other_survey_count": {"$sum": {"$cond": ["$is_own", 0, 1]}},
        }},
        {"$project": {"_id": 0}},
    ]


class QuestionUsageService(QuestionResourceService):
    def query(self, resource_id, user_id, page, page_size, version_id=None):
        resource_id = object_id(resource_id)
        version_id = object_id(version_id) if version_id is not None else None
        scope = {"resource_id": resource_id}
        if version_id is not None:
            scope["version_id"] = version_id

        def callback(session):
            now = self.clock()
            resource = self.db.Question_resources.find_one(
                {"_id": resource_id}, {"_id": 1, "owner_id": 1}, session=session
            )
            if resource is None:
                raise APIError(4040, "题目资源不存在", 404)
            owner = resource["owner_id"] == user_id
            if version_id is None and not owner:
                raise APIError(4030, "无权限", 403)
            if version_id is not None:
                version = self.db.Question_versions.find_one(
                    {"_id": version_id, "resource_id": resource_id},
                    {"_id": 1, "resource_id": 1}, session=session,
                )
                if version is None:
                    raise APIError(4040, "题目版本不存在", 404)
            authorized = owner
            if not owner:
                authorized = self.db.Question_shares.find_one({
                    "resource_id": resource_id, "version_id": version_id,
                    "recipient_id": user_id, "status": "active",
                }, {"_id": 1}, session=session) is not None
            own = next(self.db.Question_links.aggregate(
                own_pipeline(scope, user_id, page, page_size), session=session
            ))
            total = own["count"][0]["total"] if own["count"] else 0
            if not authorized and not total:
                raise APIError(4030, "没有有效授权或本人既有引用", 403)
            items = [
                {
                    "form_id": str(row["form"]["_id"]),
                    "title": row["form"]["title"],
                    "status": effective_status(row["form"], now),
                    "questions": [
                        {"question_id": str(q["question_id"]),
                         "version_id": str(q["version_id"])}
                        for q in row["questions"]
                    ],
                } for row in own["items"]
            ]
            result = {
                "resource_id": str(resource_id), "scope": "owner" if owner else "self",
                "own_survey_count": total,
                "own_surveys": {"items": items, "total": total,
                                "page": page, "page_size": page_size},
            }
            if version_id is not None:
                result["version_id"] = str(version_id)
            if owner:
                # 只有原作者执行匿名汇总，接收者路径不计算再裁剪他人信息。
                counts = list(self.db.Question_links.aggregate(
                    summary_pipeline(scope, user_id), session=session
                ))
                result.update(counts[0] if counts else {
                    "survey_count": 0, "own_survey_count": 0, "other_survey_count": 0,
                })
            return result

        return self.transaction(callback)
