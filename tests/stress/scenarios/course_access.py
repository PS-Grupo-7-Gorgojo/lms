import itertools
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class CourseAccessStressUser(HttpUser):
    """
    Simula acceso concurrente masivo a cursos y evaluaciones.

    Flujo:
      1. Login
      2. Navegar catálogo de cursos publicados
      3. Ver detalle de curso (chapters, lessons)
      4. Guardar progreso de lección (simula lectura)
      5. Consultar métricas generales (dashboard)

    Endpoints bajo estrés:
      - GET /api/resource/LMS Course (catálogo, BD read intensivo)
      - GET /api/resource/Course Chapter (estructura del curso)
      - POST save_progress (BD write por cada lección vista)
      - GET /api/method/lms.lms.api.get_chart_details (agregaciones pesadas)
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

        self._course_idx = (self._idx % 5) + 1
        self._course_title = f"Stress Course {self._course_idx}"
        self._course_name = self._fetch_course_name()
        self._chapters = []
        self._lessons = []
        if self._course_name:
            self._chapters = self._fetch_chapters()
            if self._chapters:
                self._lessons = self._fetch_lessons(self._chapters[0])

    def _fetch_course_name(self):
        resp = self.client.get(
            "/api/resource/LMS Course",
            params={
                "filters": f'[["title","=","{self._course_title}"]]',
                "fields": '["name"]',
            },
            name="GET course by title",
        )
        try:
            data = resp.json().get("data", [])
            return data[0]["name"] if data else None
        except Exception:
            return None

    def _fetch_chapters(self):
        resp = self.client.get(
            "/api/resource/Course Chapter",
            params={
                "filters": f'[["course","=","{self._course_name}"]]',
                "fields": '["name","title"]',
            },
            name="GET chapters",
        )
        try:
            return [c["name"] for c in resp.json().get("data", [])]
        except Exception:
            return []

    def _fetch_lessons(self, chapter_name):
        resp = self.client.get(
            "/api/resource/Course Lesson",
            params={
                "filters": f'[["chapter","=","{chapter_name}"]]',
                "fields": '["name"]',
            },
            name="GET lessons",
        )
        try:
            return [c["name"] for c in resp.json().get("data", [])]
        except Exception:
            return []

    @task(4)
    def browse_catalog(self):
        self.client.get(
            "/api/resource/LMS Course",
            params={
                "filters": '[["published","=",1]]',
                "limit_page_length": 20,
            },
            name="GET catalog",
        )

    @task(3)
    def view_course_detail(self):
        if not self._course_name:
            return
        self.client.get(
            f"/api/resource/LMS Course/{self._course_name}",
            name="GET course detail",
        )

    @task(2)
    def save_lesson_progress(self):
        if not self._course_name or not self._lessons:
            return
        lesson = self._lessons[self._idx % len(self._lessons)]
        self.client.post(
            "/api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress",
            json={"lesson": lesson, "course": self._course_name},
            name="POST save_progress",
        )

    @task(1)
    def check_enrollment_progress(self):
        if not self._course_name:
            return
        self.client.get(
            "/api/resource/LMS Enrollment",
            params={
                "filters": f'[["course","=","{self._course_name}"]]',
                "limit_page_length": 1,
            },
            name="GET enrollment",
        )

    @task(1)
    def get_chart_details(self):
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET chart details",
        )
