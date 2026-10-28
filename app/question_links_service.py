from copy import deepcopy

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.errors import APIError
from app.question_access import VersionAccess
from app.question_resource_service import (
    QuestionResourceService, canonical_question_content, duplicate_on, ensure_storable,
    version_output,
)
from app.question_rules import validate_form_questions
from app.survey_service import SurveyService, object_id, question_output, require_status


def link_output(link):
    return {
        "form_id": str(link["form_id"]),
        "question_id": str(link["question_id"]),
        "resource_id": str(link["resource_id"]),
        "version_id": str(link["version_id"]),
        "include_historical_answers": link["include_historical_answers"],
        "linked_at": link["linked_at"],
    }


class QuestionLinksService(QuestionResourceService):
    def import_version(self, form_id, data, user_id):
        form_id, version_id = object_id(form_id), object_id(data.version_id)
        fingerprint = self.fingerprint("import-version", str(form_id), data)
        binding = {}

        def operation(session):
            self.guard_draft(form_id, user_id, session)
            version = self.db.Question_versions.find_one(
                {"_id": version_id}, session=session
            )
            if version is None:
                raise APIError(4040, "题目版本不存在", 404)
            VersionAccess(self.db).require(
                version, user_id, session, binding, coordinate=True
            )
            return self.insert_from_version(form_id, version, data.required, session)

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def guard_draft(self, form_id, user_id, session):
        form = SurveyService.owned(self, form_id, user_id, session)
        require_status(form, "draft", self.clock())
        guarded = self.db.Question_forms.update_one(
            {"_id": form_id, "owner_id": user_id, "status": "draft"},
            {"$inc": {"revision": 1}}, session=session,
        )
        if not guarded.matched_count:
            raise APIError(4090, "问卷状态已改变", 409)

    def insert_from_version(self, form_id, version, required, session):
        # 调用者已在同一事务协调草稿及版本权限，这里不另开事务或去重。
        if self.db.Question_links.find_one(
            {"form_id": form_id, "version_id": version["_id"]}, session=session
        ):
            raise APIError(4090, "该版本已存在于当前问卷，不能重复入卷", 409)
        questions = list(self.db.Questions.find({"form_id": form_id}, session=session))
        candidate = {
            **deepcopy(version["content"]),
            "_id": ObjectId(), "form_id": form_id,
            "order": max((q["order"] for q in questions), default=0) + 1,
            "jump_rules": [],
        }
        candidate["validation"]["required"] = required
        validate_form_questions([*questions, candidate])
        if canonical_question_content(candidate) != canonical_question_content(version["content"]):
            raise APIError(4090, "卷内题目内容与目标版本不一致", 409)
        ensure_storable(candidate)
        now = self.clock()
        now = now.replace(microsecond=now.microsecond // 1000 * 1000)
        link = {
            "form_id": form_id, "question_id": candidate["_id"],
            "resource_id": version["resource_id"], "version_id": version["_id"],
            "include_historical_answers": True, "linked_at": now,
        }
        self.db.Questions.insert_one(candidate, session=session)
        self.db.Question_links.insert_one(link, session=session)
        return {**question_output(candidate), **link_output(link)}

    def question(self, form_id, question_id, user_id, session):
        SurveyService.owned(self, form_id, user_id, session)
        question = self.db.Questions.find_one(
            {"_id": question_id, "form_id": form_id}, session=session
        )
        if question is None:
            raise APIError(4040, "题目不存在", 404)
        return question

    def coordinate_form(self, form_id, user_id, session):
        SurveyService.owned(self, form_id, user_id, session)
        # 与草稿编辑、发布、关闭和提交写同一文档，关联核验不可跨状态竞态。
        self.db.Question_forms.update_one(
            {"_id": form_id, "owner_id": user_id},
            {"$inc": {"revision": 1}}, session=session,
        )

    def source(self, form_id, question_id, user_id):
        form_id, question_id = object_id(form_id), object_id(question_id)

        def callback(session):
            self.question(form_id, question_id, user_id, session)
            link = self.db.Question_links.find_one(
                {"question_id": question_id}, session=session
            )
            return link_output(link) if link else None

        return self.transaction(callback)

    def save(self, form_id, question_id, data, user_id, with_link=False):
        form_id, question_id = object_id(form_id), object_id(question_id)
        operation_name = "save-and-link" if with_link else "save"
        fingerprint = self.fingerprint(
            operation_name, f"{form_id}/{question_id}", data
        )

        def operation(session):
            if with_link:
                self.coordinate_form(form_id, user_id, session)
            question = self.question(form_id, question_id, user_id, session)
            source_link = self.db.Question_links.find_one(
                {"question_id": question_id}, session=session
            )
            if with_link and source_link:
                raise APIError(4090, "题目已关联版本；请使用显式换版操作", 409)
            content = canonical_question_content(question)
            now = self.clock()
            now = now.replace(microsecond=now.microsecond // 1000 * 1000)
            resource = {
                "_id": ObjectId(), "owner_id": user_id,
                "created_at": now, "last_version_number": 1,
            }
            version = {
                "_id": ObjectId(), "resource_id": resource["_id"],
                "version_number": 1, "parent_version_id": None,
                "change_type": "save", "created_at": now, "content": content,
                "source_form_id": form_id, "source_question_id": question_id,
            }
            if source_link:
                version.update(
                    source_resource_id=source_link["resource_id"],
                    source_version_id=source_link["version_id"],
                )
            ensure_storable(version)
            self.db.Question_resources.insert_one(resource, session=session)
            self.db.Question_versions.insert_one(version, session=session)
            result = version_output(version)
            if with_link:
                link = {
                    "form_id": form_id, "question_id": question_id,
                    "resource_id": resource["_id"], "version_id": version["_id"],
                    "include_historical_answers": True, "linked_at": now,
                }
                self.db.Question_links.insert_one(link, session=session)
                result = {**result, **link_output(link)}
            return result

        return self.execute_once(
            user_id, data.request_id, fingerprint, operation
        )

    def link(self, form_id, question_id, data, user_id):
        form_id, question_id = object_id(form_id), object_id(question_id)
        version_id = object_id(data.version_id)
        binding = {}

        def callback(session):
            question = self.question(form_id, question_id, user_id, session)
            version = self.db.Question_versions.find_one(
                {"_id": version_id}, session=session
            )
            if version is None:
                raise APIError(4040, "题目版本不存在", 404)
            VersionAccess(self.db).require(
                version, user_id, session, binding, coordinate=True
            )
            if canonical_question_content(question) != canonical_question_content(
                version["content"]
            ):
                raise APIError(4090, "卷内题目内容与目标版本不一致", 409)
            existing = self.db.Question_links.find_one(
                {"question_id": question_id}, session=session
            )
            if existing:
                if existing["version_id"] != version_id:
                    raise APIError(4090, "题目已关联其他版本", 409)
                return link_output(existing)
            self.coordinate_form(form_id, user_id, session)
            now = self.clock()
            now = now.replace(microsecond=now.microsecond // 1000 * 1000)
            link = {
                "form_id": form_id, "question_id": question_id,
                "resource_id": version["resource_id"], "version_id": version_id,
                "include_historical_answers": True, "linked_at": now,
            }
            self.db.Question_links.insert_one(link, session=session)
            return link_output(link)

        for attempt in range(3):
            try:
                return self.transaction(callback)
            except DuplicateKeyError as error:
                # 回到事务核验题目及原授权绑定，不能在事务外直接返回关联。
                if duplicate_on(error, ("question_id",)) and attempt < 2:
                    continue
                raise APIError(5000, "服务暂不可用，请稍后重试", 503) from None
