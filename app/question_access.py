from app.errors import APIError


class VersionAccess:
    def __init__(self, db):
        self.db = db

    def require(self, version, user_id, session, binding=None, coordinate=False):
        resource = self.db.Question_resources.find_one(
            {"_id": version["resource_id"]}, session=session
        )
        if resource is None:
            raise APIError(4040, "题目资源不存在", 404)
        if resource["owner_id"] == user_id:
            return True
        key = (version["resource_id"], version["_id"])
        bound = binding.get(key) if binding is not None else None
        if bound is None:
            share = self.db.Question_shares.find_one({
                "resource_id": version["resource_id"], "version_id": version["_id"],
                "recipient_id": user_id, "status": "active",
            }, session=session)
            if share is None:
                raise APIError(4030, "没有该版本的有效共享授权", 403)
            bound = (share["_id"], share["authorization_revision"])
            if binding is not None:
                # 绑定由本次调用持有，事务自动重试不能改用重新启用的授权。
                binding[key] = bound
        if coordinate:
            result = self.db.Question_shares.update_one({
                "_id": bound[0], "resource_id": version["resource_id"],
                "version_id": version["_id"], "recipient_id": user_id,
                "status": "active", "authorization_revision": bound[1],
            }, {"$inc": {"coordination_revision": 1}}, session=session)
            if not result.matched_count:
                raise APIError(4090, "共享授权已改变，请重新发起操作", 409)
        return False
