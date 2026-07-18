from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class EnrollmentStressUser(HttpUser):
    """
    Simula un estudiante navegando cursos e inscribiendose.

    Usa los endpoints REST estándar de Frappe:
      - GET  /api/resource/LMS Course?filters=...   → listar cursos
      - POST /api/resource/LMS Enrollment           → inscribirse
      - GET  /api/method/lms.lms.api.get_my_courses → mis cursos
    """
    wait_time = between(0, 1)

    def on_start(self):
        email, password = get_student_credentials(self._user_index + 1)
        resp = self.client.post(
            "/api/method/login",
            json={"usr": email, "pwd": password},
            name="POST /api/method/login",
        )
        if resp.status_code != 200:
            resp.failure(f"Login failed: {resp.text}")

    @task(3)
    def browse_courses(self):
        self.client.get(
            "/api/resource/LMS Course",
            params={
                "filters": '[["published","=",1]]',
                "limit_page_length": 20,
            },
            name="GET /api/resource/LMS Course",
        )

    @task(2)
    def enroll_in_course(self):
        idx = hash(str(self._user_index)) % 5 + 1
        course_title = f"Stress Course {idx}"
        self.client.post(
            "/api/resource/LMS Enrollment",
            json={
                "member": get_student_credentials(self._user_index + 1)[0],
                "course": course_title,
            },
            name="POST /api/resource/LMS Enrollment",
        )

    @task(1)
    def view_my_courses(self):
        self.client.get(
            "/api/method/lms.lms.api.get_my_courses",
            name="GET /api/method/lms.lms.api.get_my_courses",
        )
