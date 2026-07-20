import itertools
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class RedisQueueStressUser(HttpUser):
    """
    Satura Redis y colas RQ combinando operaciones intensivas.

    Endpoints (todos whitelisted):
      - POST create_certificate → RQ email en after_insert
      - POST save_progress → escritura BD + recálculo progreso
      - GET get_chart_details → agregaciones (COUNTs) + caché Redis
      - GET get_certified_participants → join + agregación
      - GET get_certification_details → validación de elegibilidad

    Nombres predecibles (docname = title en Frappe LMS):
      - Curso: "Redis Stress Course {1..4}"
      - Lección: "Lesson 1 - Redis Stress Course {1..4}"
    """
    wait_time = between(0, 1)
    _counter = itertools.count(1)

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

        idx = (self._idx % 4) + 1
        self._course_title = f"Redis Stress Course {idx}"
        self._lesson_title = f"Lesson 1 - Redis Stress Course {idx}"

    @task(5)
    def create_certificate(self):
        if not self._logged_in:
            return
        self.client.post(
            "/api/method/lms.lms.doctype.lms_certificate.lms_certificate.create_certificate",
            json={"course": self._course_title},
            name="POST create_certificate",
        )

    @task(4)
    def save_lesson_progress(self):
        if not self._logged_in:
            return
        self.client.post(
            "/api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress",
            json={"lesson": self._lesson_title, "course": self._course_title},
            name="POST save_progress",
        )

    @task(3)
    def get_chart_details(self):
        if not self._logged_in:
            return
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET get_chart_details",
        )

    @task(2)
    def get_certified_participants(self):
        if not self._logged_in:
            return
        self.client.get(
            "/api/method/lms.lms.api.get_certified_participants",
            name="GET get_certified_participants",
        )

    @task(1)
    def get_certification_details(self):
        if not self._logged_in:
            return
        self.client.get(
            "/api/method/lms.lms.api.get_certification_details",
            params={"course": self._course_title},
            name="GET get_certification_details",
        )
