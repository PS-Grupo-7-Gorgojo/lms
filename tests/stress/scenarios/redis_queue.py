import itertools
import json
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class RedisQueueStressUser(HttpUser):
    """
    Satura Redis y colas RQ combinando operaciones intensivas.

    Endpoints:
      - POST create_certificate (RQ email)
      - POST submit_quiz (notif)
      - POST save_progress (cache + recalculate)
      - GET get_my_courses (cache + DB)
      - GET get_chart_details (agregaciones)
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

        idx = (self._idx % 4) + 1
        self._course_title = f"Redis Stress Course {idx}"
        self._quiz_title = f"RQ Quiz - Redis Stress Course {idx}"
        self._quiz_name = self._resolve_quiz()
        self._lesson_name = self._resolve_lesson()

    def _resolve_quiz(self):
        resp = self.client.get(
            "/api/resource/LMS Quiz",
            params={
                "filters": json.dumps([["title", "=", self._quiz_title]]),
                "fields": json.dumps(["name"]),
            },
            name="GET quiz",
        )
        try:
            data = resp.json().get("data", [])
            quiz_name = data[0]["name"] if data else None
            if quiz_name:
                r = self.client.get(
                    f"/api/resource/LMS Quiz/{quiz_name}",
                    name="GET quiz detail",
                )
                self._quiz_questions = [
                    {"question_name": q["question"], "answer": ["Correct Answer"]}
                    for q in r.json().get("data", {}).get("questions", [])
                ]
            return quiz_name
        except Exception:
            return None

    def _resolve_lesson(self):
        resp = self.client.get(
            "/api/resource/Course Lesson",
            params={
                "filters": json.dumps([["course", "=", self._course_title]]),
                "fields": json.dumps(["name"]),
                "limit_page_length": 1,
            },
            name="GET lesson",
        )
        try:
            data = resp.json().get("data", [])
            return data[0]["name"] if data else None
        except Exception:
            return None

    @task(5)
    def create_certificate_rq(self):
        self.client.post(
            "/api/method/lms.lms.doctype.lms_certificate.lms_certificate.create_certificate",
            json={"course": self._course_title},
            name="POST create_certificate",
        )

    @task(4)
    def submit_quiz_rq(self):
        if not self._quiz_name or not getattr(self, "_quiz_questions", None):
            return
        self.client.post(
            "/api/method/lms.lms.doctype.lms_quiz.lms_quiz.submit_quiz",
            json={
                "quiz": self._quiz_name,
                "results": json.dumps(self._quiz_questions),
            },
            name="POST submit_quiz",
        )

    @task(3)
    def get_my_courses(self):
        self.client.get(
            "/api/method/lms.lms.api.get_my_courses",
            name="GET get_my_courses",
        )

    @task(2)
    def save_progress_cache(self):
        if not self._lesson_name:
            return
        self.client.post(
            "/api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress",
            json={"lesson": self._lesson_name, "course": self._course_title},
            name="POST save_progress",
        )

    @task(1)
    def get_chart_details(self):
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET get_chart_details",
        )
