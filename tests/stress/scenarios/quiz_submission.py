import itertools
import json
import os
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


def _load_quiz_fixture():
    fixture_path = os.path.join(
        os.path.dirname(__file__), "..", "fixtures", "quiz_data.json"
    )
    try:
        with open(fixture_path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class QuizSubmissionStressUser(HttpUser):
    """
    Entregas simultáneas de quizzes.

    Endpoints:
      - POST /api/method/lms.lms.doctype.lms_quiz.lms_quiz.submit_quiz
      - GET  /api/method/lms.lms.api.get_chart_details

    Los datos de quizzes se cargan desde el fixture JSON generado
    durante el seed, evitando llamadas REST que requieren permisos
    de doctype.
    """
    wait_time = between(0, 1)
    _counter = itertools.count(1)
    _quiz_fixture = _load_quiz_fixture()

    def on_start(self):
        self._idx = next(self.__class__._counter)
        self._logged_in = False
        email, password = get_student_credentials(self._idx)
        with self.client.post(
            "/api/method/login",
            data={"usr": email, "pwd": password},
            catch_response=True,
            name="POST /api/method/login",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Login failed ({resp.status_code})")
            else:
                self._logged_in = True
                self._setup_quiz()

    def _setup_quiz(self):
        idx = (self._idx % 3) + 1
        quiz_title = f"Quiz - Quiz Stress Course {idx}"
        self._quiz_name = quiz_title
        questions = self.__class__._quiz_fixture.get(quiz_title, [])
        self._questions = [
            {"question_name": q["name"], "answer": ["Correct Answer"]}
            for q in questions
        ]

    @task(5)
    def submit_quiz(self):
        if not self._logged_in or not self._questions:
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
    def get_chart_details(self):
        if not self._logged_in:
            return
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET get_chart_details",
        )
