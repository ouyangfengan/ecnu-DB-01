from bson import ObjectId

from app.errors import APIError
from app.question_access import VersionAccess
from app.question_resource_service import (
    QuestionResourceService, ensure_storable, version_output,
)
from app.survey_service import object_id


def share_output(share, recipient, changed=None):
    result = {
        "share_id": str(share["_id"]),
        "resource_id": str(share["resource_id"]),
        "version_id": str(share["version_id"]),
        "recipient_user_id": str(share["recipient_id"]),
        "recipient_username": recipient["username"],
        "status": share["status"],
        "authorization_revision": share["authorization_revision"],
        "created_at": share["created_at"],
        "authorized_at": share["authorized_at"],
        "revoked_at": share["revoked_at"],
    }
    if changed is not None:
        result["changed"] = changed
    return result


class QuestionSharesService(QuestionResourceService):
    def grant(self, resource_id, version_id, data, user_id):
        resource_id, version_id = object_id(resource_id), object_id(version_id)
        fingerprint = self.fingerprint("share-grant", f"{resource_id}/{version_id}", data)

        def operation(session):
            self.owned(resource_id, user_id, session)
            self.version(resource_id, version_id, session)
            recipient = self.db.Users.find_one(
                {"username": data.recipient_username}, session=session
            )
            if recipient is None:
                raise APIError(4040, "接收者用户不存在", 404)
            if recipient["_id"] == user_id:
                raise APIError(4001, "不能共享给自己", 400)
            share = self.db.Question_shares.find_one({
                "version_id": version_id, "recipient_id": recipient["_id"],
            }, session=session)
            changed = share is None or share["status"] == "revoked"
            if share is None:
                now = self.clock()
                now = now.replace(microsecond=now.microsecond // 1000 * 1000)
                share = {
                    "_id": ObjectId(), "resource_id": resource_id,
                    "version_id": version_id, "owner_id": user_id,
                    "recipient_id": recipient["_id"], "status": "active",
                    "authorization_revision": 1, "coordination_revision": 0,
                    "created_at": now, "authorized_at": now, "revoked_at": None,
                }
                self.db.Question_shares.insert_one(share, session=session)
            elif changed:
                now = self.clock()
                now = now.replace(microsecond=now.microsecond // 1000 * 1000)
                self.db.Question_shares.update_one(
                    {"_id": share["_id"]},
                    {"$set": {"status": "active", "authorized_at": now},
                     "$inc": {"authorization_revision": 1}}, session=session,
                )
                share.update(status="active", authorized_at=now)
                share["authorization_revision"] += 1
            return share_output(share, recipient, changed)

        return self.execute_once(
            user_id, data.request_id, fingerprint, operation,
            retry_unique_fields=("version_id", "recipient_id"),
        )

    def revoke(self, resource_id, version_id, share_id, data, user_id):
        resource_id, version_id, share_id = (
            object_id(resource_id), object_id(version_id), object_id(share_id)
        )
        fingerprint = self.fingerprint(
            "share-revoke", f"{resource_id}/{version_id}/{share_id}", data
        )

        def operation(session):
            self.owned(resource_id, user_id, session)
            self.version(resource_id, version_id, session)
            share = self.db.Question_shares.find_one({
                "_id": share_id, "resource_id": resource_id, "version_id": version_id,
            }, session=session)
            if share is None:
                raise APIError(4040, "共享授权不存在", 404)
            changed = share["status"] == "active"
            if changed:
                now = self.clock()
                now = now.replace(microsecond=now.microsecond // 1000 * 1000)
                self.db.Question_shares.update_one(
                    {"_id": share_id},
                    {"$set": {"status": "revoked", "revoked_at": now},
                     "$inc": {"authorization_revision": 1}}, session=session,
                )
                share.update(status="revoked", revoked_at=now)
                share["authorization_revision"] += 1
            recipient = self.db.Users.find_one(
                {"_id": share["recipient_id"]}, session=session
            )
            return share_output(share, recipient, changed)

        return self.execute_once(user_id, data.request_id, fingerprint, operation)

    def list_sent(self, resource_id, version_id, user_id, page, page_size):
        resource_id, version_id = object_id(resource_id), object_id(version_id)

        def callback(session):
            self.owned(resource_id, user_id, session)
            self.version(resource_id, version_id, session)
            query = {"resource_id": resource_id, "version_id": version_id}
            shares = self.db.Question_shares.find(query, session=session).sort(
                [("created_at", -1), ("_id", -1)]
            ).skip((page - 1) * page_size).limit(page_size)
            items = [
                share_output(share, self.db.Users.find_one(
                    {"_id": share["recipient_id"]}, session=session
                )) for share in shares
            ]
            return {
                "items": items,
                "total": self.db.Question_shares.count_documents(query, session=session),
                "page": page, "page_size": page_size,
            }

        return self.transaction(callback)

    def list_received(self, user_id, page, page_size):
        def callback(session):
            query = {"recipient_id": user_id, "status": "active"}
            shares = self.db.Question_shares.find(query, session=session).sort(
                [("authorized_at", -1), ("_id", -1)]
            ).skip((page - 1) * page_size).limit(page_size)
            items = []
            for share in shares:
                version = self.version(share["resource_id"], share["version_id"], session)
                owner = self.db.Users.find_one({"_id": share["owner_id"]}, session=session)
                items.append({
                    "share_id": str(share["_id"]),
                    "resource_id": str(share["resource_id"]),
                    "version_id": str(share["version_id"]),
                    "version_number": version["version_number"],
                    "title": version["content"]["title"], "type": version["content"]["type"],
                    "owner_username": owner["username"],
                    "authorized_at": share["authorized_at"],
                    "authorization_revision": share["authorization_revision"],
                })
            return {
                "items": items,
                "total": self.db.Question_shares.count_documents(query, session=session),
                "page": page, "page_size": page_size,
            }

        return self.transaction(callback)

    def fork(self, resource_id, version_id, data, user_id):
        resource_id, version_id = object_id(resource_id), object_id(version_id)
        fingerprint = self.fingerprint("fork", f"{resource_id}/{version_id}", data)
        binding = {}

        def operation(session):
            parent = self.version(resource_id, version_id, session)
            VersionAccess(self.db).require(
                parent, user_id, session, binding, coordinate=True
            )
            content = self.normalize_content(data, parent)
            now = self.clock()
            resource = {
                "_id": ObjectId(), "owner_id": user_id,
                "created_at": now, "last_version_number": 1,
            }
            version = {
                "_id": ObjectId(), "resource_id": resource["_id"],
                "version_number": 1, "parent_version_id": None,
                "change_type": "fork", "created_at": now, "content": content,
                "source_resource_id": resource_id, "source_version_id": version_id,
            }
            ensure_storable(version)
            self.db.Question_resources.insert_one(resource, session=session)
            self.db.Question_versions.insert_one(version, session=session)
            return version_output(version)

        return self.execute_once(user_id, data.request_id, fingerprint, operation)
