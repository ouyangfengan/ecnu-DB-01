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
