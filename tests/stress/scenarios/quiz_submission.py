import itertools
import json
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class QuizSubmissionStressUser(HttpUser):
    """
    Entregas simultáneas de quizzes.

    Endpoints:
      - POST /api/method/lms.lms.doctype.lms_quiz.lms_quiz.submit_quiz
      - GET  /api/method/lms.lms.api.get_my_courses
    """
    wait_time = between(0, 1)
    _counter = itertools.count(1)

    def on_start(self):
        self._idx = next(self.__class__._counter)
        email, password = get_student_credentials(self._idx)
        with self.client.post(
            "/api/method/login",
            data={"usr": email, "pwd": password},
            catch_response=True,
            name="POST /api/method/login",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Login failed ({resp.status_code})")
                return

        idx = (self._idx % 3) + 1
        quiz_title = f"Quiz - Quiz Stress Course {idx}"
        self._quiz_name = self._fetch_quiz_name(quiz_title)
        self._questions = []
        if self._quiz_name:
            self._questions = self._fetch_quiz_questions(self._quiz_name)

    def _fetch_quiz_name(self, quiz_title):
        resp = self.client.get(
            "/api/resource/LMS Quiz",
            params={
                "filters": json.dumps([["title", "=", quiz_title]]),
                "fields": json.dumps(["name"]),
            },
            name="GET quiz by title",
        )
        try:
            data = resp.json().get("data", [])
            return data[0]["name"] if data else None
        except Exception:
            return None

    def _fetch_quiz_questions(self, quiz_name):
        resp = self.client.get(
            f"/api/resource/LMS Quiz/{quiz_name}",
            name="GET quiz detail",
        )
        try:
            questions = resp.json().get("data", {}).get("questions", [])
            return [{"question_name": q["question"], "answer": ["Correct Answer"]} for q in questions]
        except Exception:
            return []

    @task(5)
    def submit_quiz(self):
        if not self._quiz_name or not self._questions:
            return
        self.client.post(
            "/api/method/lms.lms.doctype.lms_quiz.lms_quiz.submit_quiz",
            json={
                "quiz": self._quiz_name,
                "results": json.dumps(self._questions),
            },
            name="POST submit_quiz",
        )

    @task(1)
    def get_my_courses(self):
        self.client.get(
            "/api/method/lms.lms.api.get_my_courses",
            name="GET get_my_courses",
        )
