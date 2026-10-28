from copy import deepcopy

from bson import ObjectId
from pydantic import ValidationError
from pymongo.errors import OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from app.errors import APIError
from app.question_rules import reject, validate_form_questions
from app.security import new_token
from app.survey_schemas import QuestionInput


def object_id(value):
    if not ObjectId.is_valid(value):
        reject("ID 格式无效")
    return ObjectId(value)


def effective_status(form, now):
    if form["status"] == "published" and form.get("deadline") is not None:
        if now >= form["deadline"]:
            return "closed"
    return form["status"]


def require_status(form, expected, now):
    if form["status"] == "published" and effective_status(form, now) == "closed":
        raise APIError(4090, "问卷已截止", 409)
    if effective_status(form, now) != expected:
        messages = {"draft": "问卷尚未发布", "closed": "问卷已关闭"}
        message = messages.get(form["status"], "当前状态不允许该操作")
        if expected == "draft":
            message = "发布后不能修改问卷"
        raise APIError(4090, message, 409)


def deadline_filter(now):
    # 数据库执行更新时再次比较真实时间；注入时钟仅用于确定性测试。
    return {"$or": [
        {"deadline": None},
        {
            "deadline": {"$gt": now},
            "$expr": {"$gt": ["$deadline", "$$NOW"]},
        },
    ]}


def question_output(question):
    return {
        "question_id": str(question["_id"]),
        "order": question["order"],
        "type": question["type"],
        "title": question["title"],
        "options": question.get("options", []),
        "validation": {"required": False, **question.get("validation", {})},
        "jump_rules": question.get("jump_rules", []),
    }


class SurveyService:
    def __init__(self, request):
        self.db = request.app.state.db
        self.clock = request.app.state.clock
        self.base_url = request.app.state.settings.public_base_url.rstrip("/")

    def link(self, token):
        return f"{self.base_url}/surveys/access/{token}"

    def output(self, form, owner=False):
        result = {
            "form_id": str(form["_id"]),
            "title": form["title"],
            "description": form.get("description", ""),
            "allow_anonymous": form.get("allow_anonymous", False),
            "allow_multiple_submissions": form.get("allow_multiple_submissions", False),
            "deadline": form.get("deadline"),
            "status": effective_status(form, self.clock()),
            "created_at": form.get("created_at", form["_id"].generation_time),
        }
        if owner:
            result["access_link"] = self.link(form["access_token"])
        return result

    def transaction(self, callback):
        try:
            with self.db.client.start_session() as session:
                return session.with_transaction(
                    callback, read_concern=ReadConcern("snapshot"),
                    write_concern=WriteConcern("majority"),
                )
        except OperationFailure as error:
            if error.code in (20, 303):
                raise APIError(
                    5000, "问卷操作需要 MongoDB 副本集，请按运行说明配置", 503
                ) from None
            raise

    def owned(self, form_id, user_id, session=None):
        form = self.db.Question_forms.find_one({"_id": form_id}, session=session)
        if form is None:
            raise APIError(4040, "问卷不存在", 404)
        if form["owner_id"] != user_id:
            raise APIError(4030, "无权限", 403)
        return form

    def mutate(self, form_id, user_id, expected, operation):
        form_id = object_id(form_id)

        def callback(session):
            form = self.owned(form_id, user_id, session)
            require_status(form, expected, self.clock())
            query = {"_id": form_id, "status": expected}
            if expected == "published":
                query.update(deadline_filter(self.clock()))
            # 每次修改先写同一问卷文档，使题目编辑、发布、截止和关闭互相串行化。
            result = self.db.Question_forms.update_one(
                query, {"$inc": {"revision": 1}}, session=session
            )
            if not result.matched_count:
                raise APIError(4090, "问卷已截止或状态已改变", 409)
            return operation(form, session)

        return self.transaction(callback)

    def create(self, data, user_id):
        form = {
            "_id": ObjectId(), "owner_id": user_id,
            **data.model_dump(),
            "created_at": self.clock(), "status": "draft", "deadline": None,
            "access_token": new_token(), "revision": 0,
        }
        self.db.Question_forms.insert_one(form)
        return {"form_id": str(form["_id"]), "access_link": self.link(form["access_token"])}

    def list_owned(self, user_id, page, page_size):
        query = {"owner_id": user_id}
        cursor = self.db.Question_forms.find(query).sort(
            [("created_at", -1), ("_id", -1)]
        ).skip((page - 1) * page_size).limit(page_size)
        return {
            "items": [self.output(form, owner=True) for form in cursor],
            "total": self.db.Question_forms.count_documents(query),
            "page": page, "page_size": page_size,
        }

    def detail(self, user_id, form_id=None, access_token=None):
        parsed_id = object_id(form_id) if form_id is not None else None

        def callback(session):
            if parsed_id is not None:
                form = self.owned(parsed_id, user_id, session)
            else:
                form = self.db.Question_forms.find_one(
                    {"access_token": access_token}, session=session
                )
                if form is None:
                    raise APIError(4040, "问卷不存在", 404)
                require_status(form, "published", self.clock())
            result = self.output(form, owner=parsed_id is not None)
            result["questions"] = [
                question_output(q) for q in self.db.Questions.find(
                    {"form_id": form["_id"]}, session=session
                ).sort("order", 1)
            ]
            return result

        return self.transaction(callback)

    def responses(self, form_id, user_id, page, page_size):
        parsed_id = object_id(form_id)

        def callback(session):
            form = self.owned(parsed_id, user_id, session)
            anonymous = form.get("allow_anonymous", False)
            query = {"form_id": form["_id"]}
            documents = list(
                self.db.Responses.find(query, session=session).sort(
                    [("submitted_at", 1), ("_id", 1)]
                ).skip((page - 1) * page_size).limit(page_size)
            )
            usernames = {}
            if not anonymous:
                respondent_ids = [doc["respondent_id"] for doc in documents]
                if respondent_ids:
                    for user in self.db.Users.find(
                        {"_id": {"$in": respondent_ids}}, {"username": 1}, session=session
                    ):
                        usernames[user["_id"]] = user["username"]
            items = []
            for doc in documents:
                # 旧记录缺少 is_anonymous 时回退问卷设置，不能默认按实名展示。
                is_anonymous = doc.get("is_anonymous", anonymous)
                item = {
                    "response_id": str(doc["_id"]),
                    "submitted_at": doc["submitted_at"],
                    "is_anonymous": is_anonymous,
                    "answers": [
                        {"question_id": answer["question_id"], "value": answer["value"]}
                        for answer in doc.get("answers", [])
                    ],
                }
                if not is_anonymous:
                    respondent_id = doc["respondent_id"]
                    item["respondent_id"] = str(respondent_id)
                    item["respondent_username"] = usernames.get(respondent_id)
                items.append(item)
            return {
                "form_id": str(form["_id"]),
                "allow_anonymous": anonymous,
                "items": items,
                "total": self.db.Responses.count_documents(query, session=session),
                "page": page, "page_size": page_size,
            }

        return self.transaction(callback)

    def add_question(self, form_id, user_id, data):
        def operation(form, session):
            questions = list(self.db.Questions.find({"form_id": form["_id"]}, session=session))
            candidate = data.model_dump()
            candidate.update({
                "_id": ObjectId(), "form_id": form["_id"],
                "order": max((q["order"] for q in questions), default=0) + 1,
            })
            self.assign_options(candidate, set())
            validate_form_questions([*questions, candidate])
            self.db.Questions.insert_one(candidate, session=session)
            return question_output(candidate)

        return self.mutate(form_id, user_id, "draft", operation)

    @staticmethod
    def assign_options(question, existing_ids):
        for option in question["options"]:
            if option.get("option_id") is None:
                option["option_id"] = str(ObjectId())
            elif option["option_id"] not in existing_ids:
                reject("选项 ID 必须引用该题已有选项；新选项请省略 option_id")

    def require_version_match(self, question, session):
        link = self.db.Question_links.find_one(
            {"question_id": question["_id"]}, session=session
        )
        if link is None:
            return
        version = self.db.Question_versions.find_one(
            {"_id": link["version_id"], "resource_id": link["resource_id"]},
            session=session,
        )
        if version is None:
            raise APIError(4090, "关联的题目版本不存在", 409)
        from app.question_resource_service import canonical_question_content

        if canonical_question_content(question) != canonical_question_content(
            version["content"]
        ):
            raise APIError(4090, "版本级内容不能直接编辑；请显式换版", 409)

    def edit_question(self, form_id, question_id, user_id, patch):
        parsed_question_id = object_id(question_id)

        def operation(form, session):
            questions = list(self.db.Questions.find({"form_id": form["_id"]}, session=session))
            original = next((q for q in questions if q["_id"] == parsed_question_id), None)
            if original is None:
                raise APIError(4040, "题目不存在", 404)
            fields = ("title", "type", "options", "validation", "jump_rules")
            merged = {key: deepcopy(original[key]) for key in fields if key in original}
            merged.update(patch.model_dump(exclude_unset=True))
            try:
                candidate = QuestionInput.model_validate(merged).model_dump()
            except ValidationError as error:
                reject("题目配置无效：" + error.errors()[0]["msg"])
            candidate.update({
                "_id": original["_id"], "form_id": form["_id"], "order": original["order"],
            })
            self.assign_options(candidate, {o["option_id"] for o in original.get("options", [])})
            full = [candidate if q["_id"] == candidate["_id"] else q for q in questions]
            validate_form_questions(full)
            self.require_version_match(candidate, session)
            self.db.Questions.replace_one({"_id": candidate["_id"]}, candidate, session=session)
            return question_output(candidate)

        return self.mutate(form_id, user_id, "draft", operation)

    def set_question_required(self, form_id, question_id, user_id, required):
        parsed_question_id = object_id(question_id)

        def operation(form, session):
            questions = list(self.db.Questions.find(
                {"form_id": form["_id"]}, session=session
            ))
            original = next(
                (q for q in questions if q["_id"] == parsed_question_id), None
            )
            if original is None:
                raise APIError(4040, "题目不存在", 404)
            candidate = deepcopy(original)
            candidate.setdefault("validation", {})["required"] = required
            full = [candidate if q["_id"] == candidate["_id"] else q for q in questions]
            validate_form_questions(full)
            self.require_version_match(candidate, session)
            self.db.Questions.update_one(
                {"_id": parsed_question_id, "form_id": form["_id"]},
                {"$set": {"validation.required": required}}, session=session,
            )
            return question_output(candidate)

        return self.mutate(form_id, user_id, "draft", operation)

    def set_deadline(self, form_id, user_id, deadline):
        def operation(form, session):
            if deadline is not None and deadline <= self.clock():
                reject("截止时间必须晚于当前时间")
            self.db.Question_forms.update_one(
                {"_id": form["_id"]}, {"$set": {"deadline": deadline}}, session=session
            )
            return {"deadline": deadline}

        return self.mutate(form_id, user_id, "draft", operation)

    def publish(self, form_id, user_id):
        def operation(form, session):
            questions = list(self.db.Questions.find({"form_id": form["_id"]}, session=session))
            if not questions:
                raise APIError(4090, "请先添加题目", 409)
            validate_form_questions(questions)
            result = self.db.Question_forms.update_one(
                {"_id": form["_id"], "status": "draft", **deadline_filter(self.clock())},
                {"$set": {"status": "published"}}, session=session,
            )
            if not result.matched_count:
                raise APIError(4090, "截止时间已过，请先调整截止时间", 409)
            return {"status": "published"}

        return self.mutate(form_id, user_id, "draft", operation)

    def close(self, form_id, user_id):
        def operation(form, session):
            result = self.db.Question_forms.update_one(
                {"_id": form["_id"], "status": "published", **deadline_filter(self.clock())},
                {"$set": {"status": "closed"}}, session=session,
            )
            if not result.matched_count:
                raise APIError(4090, "问卷已截止", 409)
            return {"status": "closed"}

        return self.mutate(form_id, user_id, "published", operation)
