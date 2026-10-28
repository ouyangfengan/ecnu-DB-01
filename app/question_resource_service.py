import hashlib
import json
from copy import deepcopy

from bson import BSON, ObjectId
from bson.errors import InvalidDocument
from pydantic import ValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from app.errors import APIError
from app.question_access import VersionAccess
from app.question_resource_schemas import VersionContentInput
from app.question_rules import reject, validate_form_questions
from app.survey_service import object_id


def ensure_storable(version):
    try:
        size = len(BSON.encode(version))
    except (InvalidDocument, OverflowError, UnicodeEncodeError):
        reject("题目版本内容超出 MongoDB 存储范围")
    if size > 16 * 1024 * 1024:
        reject("题目版本内容超过 MongoDB 单文档限制")


def canonical_question_content(question):
    validation = deepcopy(question.get("validation", {}))
    if not isinstance(validation, dict):
        reject("题目校验配置无效")
    validation.pop("required", None)
    try:
        content = VersionContentInput.model_validate({
            "title": question["title"], "type": question["type"],
            "options": question.get("options", []), "validation": validation,
        }).model_dump()
    except (ValidationError, KeyError):
        reject("题目版本内容无效")
    candidate = {
        "_id": question.get("_id", ObjectId()), "order": 1,
        "jump_rules": [], **content,
    }
    validate_form_questions([candidate])
    candidate["validation"].pop("required")
    content["validation"] = candidate["validation"]
    return content


def version_output(version, include_content=False):
    result = {
        "resource_id": str(version["resource_id"]),
        "version_id": str(version["_id"]),
        "version_number": version["version_number"],
        "parent_version_id": (
            str(version["parent_version_id"]) if version["parent_version_id"] else None
        ),
        "change_type": version["change_type"],
        "created_at": version["created_at"],
    }
    if include_content:
        result["content"] = version["content"]
    if "source_question_id" in version:
        result["source_form_id"] = str(version["source_form_id"])
        result["source_question_id"] = str(version["source_question_id"])
    if "source_resource_id" in version:
        result["source_resource_id"] = str(version["source_resource_id"])
        result["source_version_id"] = str(version["source_version_id"])
    return result


def shared_version_output(version):
    # 接收者响应使用白名单，原问卷信息及未授权历史不随内容返回。
    return {
        "resource_id": str(version["resource_id"]),
        "version_id": str(version["_id"]),
        "version_number": version["version_number"],
        "created_at": version["created_at"],
        "content": version["content"],
    }


def duplicate_on(error, fields):
    details = error.details or {}
    return set(details.get("keyPattern", {})) == set(fields)


class QuestionResourceService:
    def __init__(self, request):
        self.db = request.app.state.db
        self.clock = request.app.state.clock

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
                    5000, "题目版本操作需要 MongoDB 副本集，请按运行说明配置", 503
                ) from None
            raise

    def owned(self, resource_id, user_id, session=None):
        resource = self.db.Question_resources.find_one(
            {"_id": resource_id}, session=session
        )
        if resource is None:
            raise APIError(4040, "题目资源不存在", 404)
        if resource["owner_id"] != user_id:
            raise APIError(4030, "无权限", 403)
        return resource

    def version(self, resource_id, version_id, session=None):
        version = self.db.Question_versions.find_one(
            {"_id": version_id, "resource_id": resource_id}, session=session
        )
        if version is None:
            raise APIError(4040, "题目版本不存在", 404)
        return version

    def list_owned(self, user_id, page, page_size):
        query = {"owner_id": user_id}
        resources = self.db.Question_resources.find(query).sort(
            [("created_at", -1), ("_id", -1)]
        ).skip((page - 1) * page_size).limit(page_size)
        items = []
        for resource in resources:
            latest = self.db.Question_versions.find_one({
                "resource_id": resource["_id"],
                "version_number": resource["last_version_number"],
            })
            items.append({
                "resource_id": str(resource["_id"]),
                "title": latest["content"]["title"],
                "last_version_number": resource["last_version_number"],
                "created_at": resource["created_at"],
            })
        return {
            "items": items, "total": self.db.Question_resources.count_documents(query),
            "page": page, "page_size": page_size,
        }

    def detail(self, resource_id, user_id):
        resource_id = object_id(resource_id)

        def callback(session):
            resource = self.owned(resource_id, user_id, session)
            versions = self.db.Question_versions.find(
                {"resource_id": resource_id}, session=session
            ).sort("version_number", 1)
            return {
                "resource_id": str(resource_id),
                "created_at": resource["created_at"],
                "versions": [version_output(version) for version in versions],
            }

        return self.transaction(callback)

    def version_detail(self, resource_id, version_id, user_id):
        resource_id, version_id = object_id(resource_id), object_id(version_id)

        def callback(session):
            version = self.version(resource_id, version_id, session)
            owner = VersionAccess(self.db).require(version, user_id, session)
            return (
                version_output(version, include_content=True) if owner
                else shared_version_output(version)
            )

        return self.transaction(callback)

    @staticmethod
    def normalize_content(data, parent=None):
        content = data.model_dump(
            exclude={"request_id", "parent_version_id", "expected_version_id"}
        )
        existing = {
            option["option_id"]: option["text"]
            for option in parent["content"]["options"]
        } if parent is not None else {}
        for option in content["options"]:
            try:
                option["text"].encode("utf-8")
            except UnicodeEncodeError:
                reject("选项包含无效字符")
            if option["option_id"] is None:
                option["option_id"] = str(ObjectId())
            elif existing.get(option["option_id"]) != option["text"]:
                reject("选项 ID 只能保留来源版本中未改变的选项")
        question = {
            "_id": ObjectId(), "order": 1, "jump_rules": [],
            **deepcopy(content),
        }
        validate_form_questions([question])
        question["validation"].pop("required")
        content["validation"] = question["validation"]
        return content

    @staticmethod
    def fingerprint(operation, target, data):
        try:
            payload = json.dumps(
                {"operation": operation, "target": target,
                 "body": data.model_dump(mode="json", by_alias=True)},
                sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError):
            reject("请求内容必须是有效 JSON，不能包含 NaN 或无穷大")
        return hashlib.sha256(payload).hexdigest()

    def replay(self, user_id, request_id, fingerprint, session=None):
        record = self.db.Question_operations.find_one(
            {"user_id": user_id, "request_id": request_id}, session=session
        )
        if record is None:
            return None
        if record["fingerprint"] != fingerprint:
            raise APIError(4090, "请求标识已用于其他题目操作", 409)
        return record["result"]

    def execute_once(self, user_id, request_id, fingerprint, operation,
                     retry_unique_fields=None):
        existing = self.replay(user_id, request_id, fingerprint)
        if existing is not None:
            return existing

        def callback(session):
            existing = self.replay(user_id, request_id, fingerprint, session)
            if existing is not None:
                return existing
            marker = {
                "user_id": user_id, "request_id": request_id,
                "fingerprint": fingerprint,
            }
            self.db.Question_operations.insert_one(marker, session=session)
            result = operation(session)
            self.db.Question_operations.update_one(
                {"_id": marker["_id"]}, {"$set": {"result": result}}, session=session
            )
            return result

        for attempt in range(3):
            try:
                return self.transaction(callback)
            except DuplicateKeyError as error:
                existing = self.replay(user_id, request_id, fingerprint)
                if existing is not None:
                    return existing
                # 授权首次创建的唯一键竞争需重新核验，不等同于请求去重竞争。
                if (retry_unique_fields and duplicate_on(error, retry_unique_fields)
                        and attempt < 2):
                    continue
                raise APIError(5000, "服务暂不可用，请稍后重试", 503) from None

    def create(self, data, user_id):
        fingerprint = self.fingerprint("create", "", data)

        def operation(session):
            content = self.normalize_content(data)
            now = self.clock()
            resource = {
                "_id": ObjectId(), "owner_id": user_id,
                "created_at": now, "last_version_number": 1,
            }
            version = {
                "_id": ObjectId(), "resource_id": resource["_id"],
                "version_number": 1, "parent_version_id": None,
                "change_type": "create", "created_at": now, "content": content,
            }
            ensure_storable(version)
            self.db.Question_resources.insert_one(resource, session=session)
            self.db.Question_versions.insert_one(version, session=session)
            return version_output(version)

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def insert_derived_version(self, resource_id, user_id, source_id, change_type,
                               session, data=None):
        self.owned(resource_id, user_id, session)
        parent = self.version(resource_id, source_id, session)
        content = (
            deepcopy(parent["content"]) if data is None
            else self.normalize_content(data, parent)
        )
        resource = self.db.Question_resources.find_one_and_update(
            {"_id": resource_id, "owner_id": user_id},
            {"$inc": {"last_version_number": 1}},
            return_document=ReturnDocument.AFTER, session=session,
        )
        version = {
            "_id": ObjectId(), "resource_id": resource_id,
            "version_number": resource["last_version_number"],
            "parent_version_id": source_id, "change_type": change_type,
            "created_at": self.clock(), "content": content,
        }
        ensure_storable(version)
        self.db.Question_versions.insert_one(version, session=session)
        return version

    def append_version(self, resource_id, user_id, request_id, fingerprint, source_id,
                       change_type, data=None):
        def operation(session):
            return version_output(self.insert_derived_version(
                resource_id, user_id, source_id, change_type, session, data
            ))

        return self.execute_once(user_id, request_id, fingerprint, operation)

    def derive(self, resource_id, data, user_id):
        resource_id = object_id(resource_id)
        source_id = object_id(data.parent_version_id)
        fingerprint = self.fingerprint("derive", str(resource_id), data)
        return self.append_version(
            resource_id, user_id, data.request_id, fingerprint, source_id, "derive", data
        )

    def restore(self, resource_id, version_id, data, user_id):
        resource_id, source_id = object_id(resource_id), object_id(version_id)
        fingerprint = self.fingerprint(
            "restore", f"{resource_id}/{source_id}", data
        )
        return self.append_version(
            resource_id, user_id, data.request_id, fingerprint, source_id, "restore"
        )
