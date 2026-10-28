from copy import deepcopy

from app.errors import APIError
from app.question_access import VersionAccess
from app.question_links_service import QuestionLinksService, link_output
from app.question_resource_service import canonical_question_content, ensure_storable
from app.question_rules import validate_form_questions
from app.survey_service import SurveyService, object_id, question_output, require_status


class QuestionSwitchService(QuestionLinksService):
    def switch(self, form_id, question_id, data, user_id, derive=False):
        form_id, question_id = object_id(form_id), object_id(question_id)
        expected = object_id(data.expected_version_id)
        target_id = object_id(data.parent_version_id if derive else data.version_id)
        fingerprint = self.fingerprint(
            "derive-and-switch" if derive else "switch-version",
            f"{form_id}/{question_id}", data,
        )
        binding = {}

        def operation(session):
            form = SurveyService.owned(self, form_id, user_id, session)
            require_status(form, "draft", self.clock())
            guarded = self.db.Question_forms.update_one(
                {"_id": form_id, "owner_id": user_id, "status": "draft"},
                {"$inc": {"revision": 1}}, session=session,
            )
            if not guarded.matched_count:
                raise APIError(4090, "问卷状态已改变", 409)
            original = self.question(form_id, question_id, user_id, session)
            current = self.db.Question_links.find_one(
                {"form_id": form_id, "question_id": question_id}, session=session
            )
            if current is None:
                raise APIError(4090, "题目尚未关联版本，请先保存或关联", 409)
            if current["version_id"] != expected:
                raise APIError(4090, "当前关联版本已改变，请刷新后重试", 409)
            if derive:
                self.owned(current["resource_id"], user_id, session)
            SurveyService.require_version_match(self, original, session)
            target = self.db.Question_versions.find_one(
                {"_id": target_id}, session=session
            )
            if target is None:
                raise APIError(4040, "题目版本不存在", 404)
            if target["resource_id"] != current["resource_id"]:
                raise APIError(4090, "只允许同一资源内换版", 409)
            if not derive and target["_id"] != current["version_id"]:
                VersionAccess(self.db).require(
                    target, user_id, session, binding, coordinate=True
                )
            if derive:
                target = self.insert_derived_version(
                    current["resource_id"], user_id, target_id, "derive",
                    session, data,
                )
            changed = target["_id"] != current["version_id"]
            if changed and self.db.Question_links.find_one({
                "form_id": form_id, "version_id": target["_id"],
                "question_id": {"$ne": question_id},
            }, session=session):
                raise APIError(4090, "目标版本已存在于当前问卷，不能重复使用", 409)
            candidate = deepcopy(original)
            candidate.update(deepcopy(target["content"]))
            candidate["validation"]["required"] = original.get(
                "validation", {}
            ).get("required", False)
            questions = list(self.db.Questions.find(
                {"form_id": form_id}, session=session
            ))
            validate_form_questions([
                candidate if q["_id"] == question_id else q for q in questions
            ])
            if canonical_question_content(candidate) != canonical_question_content(
                target["content"]
            ):
                raise APIError(4090, "卷内题目内容与目标版本不一致", 409)
            ensure_storable(candidate)
            if changed:
                self.db.Questions.replace_one(
                    {"_id": question_id, "form_id": form_id}, candidate, session=session
                )
                self.db.Question_links.update_one(
                    {"_id": current["_id"], "version_id": expected},
                    {"$set": {"version_id": target["_id"]}}, session=session,
                )
                current["version_id"] = target["_id"]
            return {
                **question_output(candidate), **link_output(current),
                "changed": changed,
            }

        return self.execute_once(user_id, data.request_id, fingerprint, operation)
