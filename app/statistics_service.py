from app.errors import APIError
from app.statistics_pipeline import STATISTIC_HANDLERS
from app.survey_service import SurveyService, object_id


class StatisticsService(SurveyService):
    def submission_count(self, form_id, session):
        return self.db.Responses.count_documents({"form_id": form_id}, session=session)

    def summarize_question(self, form_id, question, session, page=1, page_size=20):
        handler = STATISTIC_HANDLERS.get(question["type"])
        if handler is None:
            raise APIError(5000, "当前题型尚未配置统计方式", 500)
        return {
            "question_id": str(question["_id"]),
            "order": question["order"],
            "type": question["type"],
            "title": question["title"],
            **handler(self.db, form_id, question, session, page, page_size),
        }

    def whole_form(self, form_id, user_id):
        parsed_id = object_id(form_id)

        def callback(session):
            # 权限、题目配置、总数和每题聚合共享同一个事务快照。
            form = self.owned(parsed_id, user_id, session)
            questions = list(self.db.Questions.find(
                {"form_id": parsed_id}, session=session
            ).sort([("order", 1), ("_id", 1)]))
            total = self.submission_count(parsed_id, session)
            return {
                **self.output(form),
                "submission_count": total,
                "questions": [
                    self.summarize_question(parsed_id, question, session)
                    for question in questions
                ],
            }

        return self.transaction(callback)

    def one_question(self, form_id, question_id, user_id, page, page_size):
        parsed_id, parsed_qid = object_id(form_id), object_id(question_id)

        def callback(session):
            self.owned(parsed_id, user_id, session)
            question = self.db.Questions.find_one(
                {"_id": parsed_qid, "form_id": parsed_id}, session=session
            )
            if question is None:
                raise APIError(4040, "题目不存在", 404)
            return {
                "form_id": str(parsed_id),
                "submission_count": self.submission_count(parsed_id, session),
                "question": self.summarize_question(
                    parsed_id, question, session, page, page_size
                ),
            }

        return self.transaction(callback)
