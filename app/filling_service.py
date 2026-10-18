import hashlib
import json
from datetime import timezone

from bson import BSON, ObjectId
from pymongo.errors import DuplicateKeyError

from app.answer_engine import canonical_answers, replay_answers
from app.errors import APIError
from app.survey_service import SurveyService, deadline_filter, require_status


def request_fingerprint(answers):
    try:
        encoded = json.dumps(
            canonical_answers(answers), sort_keys=True, ensure_ascii=True,
            allow_nan=False, separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError):
        raise APIError(4001, "答案必须是有效 JSON，不能包含 NaN 或无穷大", 400) from None
    return hashlib.sha256(encoded).hexdigest()


def submission_output(document):
    return {
        "response_id": str(document["_id"]),
        "submitted_at": document["submitted_at"],
    }


def replay_submission(document, fingerprint):
    if document.get("request_hash") != fingerprint:
        raise APIError(4090, "请求标识已用于其他提交内容", 409)
    return submission_output(document)


class FillingService(SurveyService):
    def linked_form(self, token, session=None):
        form = self.db.Question_forms.find_one({"access_token": token}, session=session)
        if form is None:
            raise APIError(4040, "问卷不存在", 404)
        return form

    def check_submission_limit(self, form, user_id, session):
        if not form.get("allow_multiple_submissions", False):
            if self.db.Responses.find_one(
                {"form_id": form["_id"], "respondent_id": user_id},
                {"_id": 1}, session=session,
            ):
                raise APIError(4090, "该问卷不允许重复提交", 409)

    def progress(self, token, user_id, answers):
        def callback(session):
            form = self.linked_form(token, session)
            require_status(form, "published", self.clock())
            self.check_submission_limit(form, user_id, session)
            questions = list(self.db.Questions.find({"form_id": form["_id"]}, session=session))
            return replay_answers(questions, answers)

        return self.transaction(callback)

    def submit(self, token, user_id, request_id, answers):
        fingerprint = request_fingerprint(answers)
        form = self.linked_form(token)
        key = {
            "form_id": form["_id"], "respondent_id": user_id, "request_id": request_id,
        }
        existing = self.db.Responses.find_one(key)
        if existing is not None:
            # 幂等回放先于开放状态及次数检查，截止或关闭不撤销已经成功的提交。
            return replay_submission(existing, fingerprint)

        def callback(session):
            current_form = self.linked_form(token, session)
            existing = self.db.Responses.find_one(key, session=session)
            if existing is not None:
                return replay_submission(existing, fingerprint)
            require_status(current_form, "published", self.clock())
            self.check_submission_limit(current_form, user_id, session)
            questions = list(self.db.Questions.find(
                {"form_id": current_form["_id"]}, session=session
            ))
            result = replay_answers(questions, answers, final=True)
            now = self.clock().astimezone(timezone.utc)
            now = now.replace(microsecond=now.microsecond // 1000 * 1000)
            document = {
                "_id": ObjectId(),
                **key,
                "request_hash": fingerprint,
                "submitted_at": now,
                "is_anonymous": current_form.get("allow_anonymous", False),
                "single_submission": not current_form.get("allow_multiple_submissions", False),
                "answers": [item for item in result["answers"] if item["value"] is not None],
            }
            if len(BSON.encode(document)) > 16 * 1024 * 1024:
                raise APIError(4001, "答案总量超过 MongoDB 单文档限制", 400)
            self.db.Responses.insert_one(document, session=session)
            # 与关闭接口写同一个问卷文档，消除只读快照导致的关闭/提交竞态。
            guarded = self.db.Question_forms.update_one(
                {
                    "_id": current_form["_id"], "status": "published",
                    **deadline_filter(self.clock()),
                },
                {"$inc": {"revision": 1}}, session=session,
            )
            if not guarded.matched_count:
                require_status(current_form, "published", self.clock())
                raise APIError(4090, "问卷已截止或状态已改变", 409)
            return submission_output(document)

        try:
            return self.transaction(callback)
        except DuplicateKeyError:
            # 并发提交可能在唯一索引处相遇；事务回滚后重读，不能把重试误报为冲突。
            existing = self.db.Responses.find_one(key)
            if existing is not None:
                return replay_submission(existing, fingerprint)
            self.check_submission_limit(form, user_id, session=None)
            raise APIError(5000, "服务暂不可用，请稍后重试", 503) from None
