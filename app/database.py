def create_indexes(db):
    db.Users.create_index("username", unique=True, name="unique_username")
    db.Sessions.create_index("user_id", unique=True, name="one_session_per_user")
    db.Sessions.create_index("token_hash", unique=True, name="unique_token_hash")
    db.Sessions.create_index(
        "expires_at", expireAfterSeconds=0, name="expired_sessions"
    )
    db.Question_forms.create_index(
        "access_token", unique=True, sparse=True, name="unique_access_token"
    )
    db.Question_forms.create_index(
        [("owner_id", 1), ("created_at", -1), ("_id", -1)], name="owner_newest"
    )
    db.Questions.create_index(
        [("form_id", 1), ("order", 1)], unique=True, name="unique_form_order",
        partialFilterExpression={"form_id": {"$exists": True}, "order": {"$exists": True}},
    )
    db.Question_resources.create_index(
        [("owner_id", 1), ("created_at", -1), ("_id", -1)],
        name="owner_resources_newest",
    )
    db.Question_versions.create_index(
        [("resource_id", 1), ("version_number", 1)],
        unique=True, name="unique_resource_version",
    )
    db.Question_operations.create_index(
        [("user_id", 1), ("request_id", 1)],
        unique=True, name="unique_question_operation",
    )
    db.Question_links.create_index(
        "question_id", unique=True, name="unique_question_link",
    )
    db.Question_links.create_index(
        [("resource_id", 1), ("form_id", 1), ("question_id", 1)],
        name="resource_usage",
    )
    db.Question_links.create_index(
        [("resource_id", 1), ("version_id", 1), ("form_id", 1), ("question_id", 1)],
        name="version_usage",
    )
    db.Question_shares.create_index(
        [("version_id", 1), ("recipient_id", 1)],
        unique=True, name="unique_version_recipient",
    )
    db.Question_shares.create_index(
        [("recipient_id", 1), ("status", 1), ("authorized_at", -1), ("_id", -1)],
        name="recipient_active_newest",
    )
    db.Question_shares.create_index(
        [("resource_id", 1), ("version_id", 1), ("created_at", -1), ("_id", -1)],
        name="version_shares_newest",
    )
    db.Question_banks.create_index(
        [("owner_id", 1), ("created_at", -1), ("_id", -1)], name="owner_banks_newest",
    )
    db.Question_bank_members.create_index(
        [("bank_id", 1), ("resource_id", 1)], unique=True, name="unique_bank_resource",
    )
    db.Question_bank_members.create_index(
        [("bank_id", 1), ("added_at", -1), ("_id", -1)], name="bank_members_newest",
    )
    db.Responses.create_index(
        [("form_id", 1), ("respondent_id", 1), ("request_id", 1)],
        unique=True, name="unique_submission_request",
        partialFilterExpression={"request_id": {"$type": "string"}},
    )
    db.Responses.create_index(
        [("form_id", 1), ("respondent_id", 1)],
        unique=True, name="one_submission_per_user",
        partialFilterExpression={"single_submission": True},
    )
    db.Responses.create_index(
        [("form_id", 1), ("respondent_id", 1), ("submitted_at", -1)],
        name="form_respondent_time",
    )
    db.Responses.create_index(
        [("form_id", 1), ("answers.question_id", 1), ("submitted_at", 1), ("_id", 1)],
        name="form_question_oldest",
    )
