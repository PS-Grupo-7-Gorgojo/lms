import itertools
import json
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class RedisQueueStressUser(HttpUser):
    """
    Satura Redis y colas RQ combinando operaciones intensivas.

    Cada usuario ejecuta un mix de operaciones que generan tráfico a:
      - Redis cache (lecturas de catálogo, dashboard, sesiones)
      - RQ "long" queue (recalculate_progress al crear lecciones)
      - RQ "short" queue (envío de emails al emitir certificados)
      - BD reads/writes masivas (quiz submissions, progress saves)

    Flujo:
      1. Login
      2. Resolver nombres de curso, quiz, lección vía API
      3. Ejecutar tareas en peso proporcional a su impacto en Redis/RQ
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
        self._course_name = self._resolve_course()
        self._quiz_name = self._resolve_quiz()
        self._lesson_name = self._resolve_lesson()

    def _resolve_course(self):
        resp = self.client.get(
            "/api/resource/LMS Course",
            params={
                "filters": f'[["title","=","{self._course_title}"]]',
                "fields": '["name"]',
            },
            name="GET course",
        )
        try:
            data = resp.json().get("data", [])
            return data[0]["name"] if data else None
        except Exception:
            return None

    def _resolve_quiz(self):
        title = f"RQ Quiz - {self._course_title}"
        resp = self.client.get(
            "/api/resource/LMS Quiz",
            params={
                "filters": f'[["title","=","{title}"]]',
                "fields": '["name"]',
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
        if not self._course_name:
            return None
        resp = self.client.get(
            "/api/resource/Course Lesson",
            params={
                "filters": f'[["course","=","{self._course_name}"]]',
                "fields": '["name"]',
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
        if not self._course_title:
            return
        self.client.post(
            "/api/method/lms.lms.doctype.lms_certificate.lms_certificate.create_certificate",
            json={"course": self._course_title},
            name="POST create_certificate (RQ email)",
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
            name="POST submit_quiz (notif)",
        )

    @task(3)
    def save_progress_cache(self):
        if not self._course_name or not self._lesson_name:
            return
        self.client.post(
            "/api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress",
            json={"lesson": self._lesson_name, "course": self._course_name},
            name="POST save_progress (cache)",
        )

    @task(2)
    def browse_catalog_cache(self):
        self.client.get(
            "/api/resource/LMS Course",
            params={
                "filters": '[["published","=",1]]',
                "limit_page_length": 20,
            },
            name="GET catalog (cache)",
        )

    @task(1)
    def dashboard_aggregations(self):
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET chart details (aggr)",
        )
