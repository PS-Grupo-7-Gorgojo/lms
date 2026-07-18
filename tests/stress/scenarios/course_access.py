import itertools
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class CourseAccessStressUser(HttpUser):
    """
    Acceso concurrente masivo a cursos y evaluaciones.

    Endpoints:
      - GET /api/method/lms.lms.api.get_my_courses
      - GET /api/method/lms.lms.api.get_chart_details
      - GET /api/method/lms.lms.api.get_certified_participants
      - POST /api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress
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

        self._course_title = f"Stress Course {(self._idx % 5) + 1}"

    @task(4)
    def browse_my_courses(self):
        self.client.get(
            "/api/method/lms.lms.api.get_my_courses",
            name="GET get_my_courses",
        )

    @task(3)
    def get_chart_details(self):
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET get_chart_details",
        )

    @task(2)
    def save_lesson_progress(self):
        self.client.post(
            "/api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress",
            json={"lesson": self._course_title, "course": self._course_title},
            name="POST save_progress",
        )

    @task(1)
    def get_certified_participants(self):
        self.client.get(
            "/api/method/lms.lms.api.get_certified_participants",
            name="GET get_certified_participants",
        )
