from bson import ObjectId

from app.errors import APIError
from app.question_access import VersionAccess
from app.question_links_service import QuestionLinksService
from app.survey_service import object_id


def bank_output(bank, changed=None):
    result = {
        "bank_id": str(bank["_id"]), "name": bank["name"],
        "description": bank["description"],
        "created_at": bank["created_at"], "updated_at": bank["updated_at"],
    }
    if changed is not None:
        result["changed"] = changed
    return result


def member_output(member, changed=None):
    result = {
        "member_id": str(member["_id"]), "bank_id": str(member["bank_id"]),
        "resource_id": str(member["resource_id"]), "version_id": str(member["version_id"]),
        "added_at": member["added_at"], "updated_at": member["updated_at"],
    }
    if changed is not None:
        result["changed"] = changed
    return result


class QuestionBanksService(QuestionLinksService):
    def now(self):
        value = self.clock()
        return value.replace(microsecond=value.microsecond // 1000 * 1000)

    def bank_owned(self, bank_id, user_id, session):
        bank = self.db.Question_banks.find_one({"_id": bank_id}, session=session)
        if bank is None:
            raise APIError(4040, "题库不存在", 404)
        if bank["owner_id"] != user_id:
            raise APIError(4030, "无权限", 403)
        return bank

    def coordinate_bank(self, bank_id, user_id, session):
        bank = self.bank_owned(bank_id, user_id, session)
        self.db.Question_banks.update_one(
            {"_id": bank_id, "owner_id": user_id},
            {"$inc": {"revision": 1}}, session=session,
        )
        return bank

    def member(self, bank_id, member_id, session):
        member = self.db.Question_bank_members.find_one(
            {"_id": member_id, "bank_id": bank_id}, session=session
        )
        if member is None:
            raise APIError(4040, "题库成员不存在", 404)
        return member

    def target(self, version_id, user_id, binding, session):
        version = self.db.Question_versions.find_one(
            {"_id": version_id}, {"_id": 1, "resource_id": 1}, session=session
        )
        if version is None:
            raise APIError(4040, "题目版本不存在", 404)
        VersionAccess(self.db).require(
            version, user_id, session, binding, coordinate=True
        )
        return version

    def create(self, data, user_id):
        fingerprint = self.fingerprint("bank-create", "", data)

        def operation(session):
            now = self.now()
            bank = {
                "_id": ObjectId(), "owner_id": user_id, "name": data.name,
                "description": data.description, "revision": 0,
                "created_at": now, "updated_at": now,
            }
            self.db.Question_banks.insert_one(bank, session=session)
            return bank_output(bank, changed=True)

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def list_banks(self, user_id, page, page_size):
        def callback(session):
            query = {"owner_id": user_id}
            banks = self.db.Question_banks.find(query, session=session).sort(
                [("created_at", -1), ("_id", -1)]
            ).skip((page - 1) * page_size).limit(page_size)
            return {
                "items": [bank_output(b) for b in banks],
                "total": self.db.Question_banks.count_documents(query, session=session),
                "page": page, "page_size": page_size,
            }

        return self.transaction(callback)

    def detail(self, bank_id, user_id):
        bank_id = object_id(bank_id)
        return self.transaction(lambda session: bank_output(
            self.bank_owned(bank_id, user_id, session)
        ))

    def patch(self, bank_id, data, user_id):
        bank_id = object_id(bank_id)
        fingerprint = self.fingerprint("bank-patch", str(bank_id), data)
        fields = data.model_dump(exclude_unset=True, exclude={"request_id"})

        def operation(session):
            bank = self.coordinate_bank(bank_id, user_id, session)
            changed = any(bank[key] != value for key, value in fields.items())
            if changed:
                updates = {**fields, "updated_at": self.now()}
                self.db.Question_banks.update_one(
                    {"_id": bank_id}, {"$set": updates}, session=session
                )
                bank.update(updates)
            return bank_output(bank, changed)

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def list_members(self, bank_id, user_id, page, page_size):
        bank_id = object_id(bank_id)

        def callback(session):
            self.bank_owned(bank_id, user_id, session)
            query = {"bank_id": bank_id}
            members = self.db.Question_bank_members.find(query, session=session).sort(
                [("added_at", -1), ("_id", -1)]
            ).skip((page - 1) * page_size).limit(page_size)
            items = []
            for member in members:
                result = member_output(member)
                resource = self.db.Question_resources.find_one(
                    {"_id": member["resource_id"]},
                    {"_id": 1, "owner_id": 1}, session=session,
                )
                version = self.db.Question_versions.find_one({
                    "_id": member["version_id"], "resource_id": member["resource_id"],
                }, {"_id": 1, "resource_id": 1}, session=session)
                # 成员关系不授予权限，归属异常或失效授权都不能带出内容。
                available = bool(resource and version)
                if available and resource["owner_id"] != user_id:
                    available = self.db.Question_shares.find_one({
                        "resource_id": member["resource_id"], "version_id": member["version_id"],
                        "recipient_id": user_id, "status": "active",
                    }, {"_id": 1}, session=session) is not None
                result["available"] = available
                if available:
                    content = self.db.Question_versions.find_one({
                        "_id": member["version_id"], "resource_id": member["resource_id"],
                    }, {"_id": 0, "content.title": 1, "content.type": 1}, session=session)
                    result.update(title=content["content"]["title"], type=content["content"]["type"])
                items.append(result)
            return {
                "items": items,
                "total": self.db.Question_bank_members.count_documents(query, session=session),
                "page": page, "page_size": page_size,
            }

        return self.transaction(callback)

    def add_member(self, bank_id, data, user_id):
        bank_id, version_id = object_id(bank_id), object_id(data.version_id)
        fingerprint = self.fingerprint("bank-add", str(bank_id), data)
        binding = {}

        def operation(session):
            self.coordinate_bank(bank_id, user_id, session)
            version = self.target(version_id, user_id, binding, session)
            existing = self.db.Question_bank_members.find_one({
                "bank_id": bank_id, "resource_id": version["resource_id"],
            }, session=session)
            if existing:
                if existing["version_id"] != version_id:
                    raise APIError(4090, "该资源已在题库中，请显式更新版本", 409)
                return member_output(existing, changed=False)
            now = self.now()
            member = {
                "_id": ObjectId(), "bank_id": bank_id, "resource_id": version["resource_id"],
                "version_id": version_id, "added_at": now, "updated_at": now,
            }
            self.db.Question_bank_members.insert_one(member, session=session)
            return member_output(member, changed=True)

        return self.execute_once(
            user_id, data.request_id, fingerprint, operation,
            retry_unique_fields=("bank_id", "resource_id"),
        )

    def switch_member(self, bank_id, member_id, data, user_id):
        bank_id, member_id = object_id(bank_id), object_id(member_id)
        expected, version_id = object_id(data.expected_version_id), object_id(data.version_id)
        fingerprint = self.fingerprint("bank-switch", f"{bank_id}/{member_id}", data)
        binding = {}

        def operation(session):
            self.coordinate_bank(bank_id, user_id, session)
            member = self.member(bank_id, member_id, session)
            if member["version_id"] != expected:
                raise APIError(4090, "成员版本已改变，请重新确认", 409)
            version = self.db.Question_versions.find_one(
                {"_id": version_id}, {"_id": 1, "resource_id": 1}, session=session
            )
            if version is None:
                raise APIError(4040, "题目版本不存在", 404)
            if version["resource_id"] != member["resource_id"]:
                raise APIError(4090, "只允许同一资源内更新题库版本", 409)
            VersionAccess(self.db).require(version, user_id, session, binding, coordinate=True)
            changed = expected != version_id
            if changed:
                updates = {"version_id": version_id, "updated_at": self.now()}
                self.db.Question_bank_members.update_one(
                    {"_id": member_id, "bank_id": bank_id}, {"$set": updates}, session=session
                )
                member.update(updates)
            return member_output(member, changed)

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def remove_member(self, bank_id, member_id, data, user_id):
        bank_id, member_id = object_id(bank_id), object_id(member_id)
        fingerprint = self.fingerprint("bank-remove", f"{bank_id}/{member_id}", data)

        def operation(session):
            self.coordinate_bank(bank_id, user_id, session)
            self.member(bank_id, member_id, session)
            self.db.Question_bank_members.delete_one(
                {"_id": member_id, "bank_id": bank_id}, session=session
            )
            return {"bank_id": str(bank_id), "member_id": str(member_id), "deleted": True}

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def delete(self, bank_id, data, user_id):
        bank_id = object_id(bank_id)
        fingerprint = self.fingerprint("bank-delete", str(bank_id), data)

        def operation(session):
            self.coordinate_bank(bank_id, user_id, session)
            removed = self.db.Question_bank_members.delete_many({"bank_id": bank_id}, session=session)
            self.db.Question_banks.delete_one({"_id": bank_id}, session=session)
            return {"bank_id": str(bank_id), "deleted": True,
                    "removed_member_count": removed.deleted_count}

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def import_member(self, form_id, data, user_id):
        form_id = object_id(form_id)
        bank_id, member_id = object_id(data.bank_id), object_id(data.member_id)
        expected = object_id(data.expected_member_version_id)
        fingerprint = self.fingerprint("import-bank", str(form_id), data)
        binding = {}

        def operation(session):
            self.coordinate_bank(bank_id, user_id, session)
            member = self.member(bank_id, member_id, session)
            if member["version_id"] != expected:
                raise APIError(4090, "成员版本已改变，请重新确认", 409)
            version = self.db.Question_versions.find_one({
                "_id": member["version_id"], "resource_id": member["resource_id"],
            }, session=session)
            if version is None:
                raise APIError(4040, "成员版本不存在或归属不一致", 404)
            VersionAccess(self.db).require(version, user_id, session, binding, coordinate=True)
            self.guard_draft(form_id, user_id, session)
            result = self.insert_from_version(form_id, version, data.required, session)
            return {**result, "bank_id": str(bank_id), "member_id": str(member_id)}

        return self.execute_once(user_id, data.request_id, fingerprint, operation)
