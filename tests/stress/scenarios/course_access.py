import itertools
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class CourseAccessStressUser(HttpUser):
    """
    Acceso concurrente masivo a cursos y evaluaciones.

    Endpoints:
      - GET /api/method/lms.lms.api.get_chart_details
      - GET /api/method/lms.lms.api.get_certified_participants
      - GET /api/method/lms.lms.api.get_certification_details
      - POST /api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress
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

        self._course_title = f"Stress Course {(self._idx % 5) + 1}"

    @task(4)
    def get_chart_details(self):
        if not self._logged_in:
            return
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET get_chart_details",
        )

    @task(3)
    def get_certified_participants(self):
        if not self._logged_in:
            return
        self.client.get(
            "/api/method/lms.lms.api.get_certified_participants",
            name="GET get_certified_participants",
        )

    @task(2)
    def get_certification_details(self):
        if not self._logged_in:
            return
        idx = (self._idx % 5) + 1
        course_title = f"Stress Course {idx}"
        self.client.get(
            "/api/method/lms.lms.api.get_certification_details",
            params={"course": course_title},
            name="GET get_certification_details",
        )

    @task(1)
    def save_lesson_progress(self):
        if not self._logged_in:
            return
        self.client.post(
            "/api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress",
            json={"lesson": self._course_title, "course": self._course_title},
            name="POST save_progress",
        )
