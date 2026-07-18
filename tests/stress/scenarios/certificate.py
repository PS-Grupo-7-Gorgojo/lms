from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class CertificateStressUser(HttpUser):
    """
    Simula estudiantes solicitando certificados masivamente al completar un curso.

    Flujo:
      1. Login como estudiante con curso completado al 100%
      2. Solicitar emisión de certificado (create_certificate)
      3. Verificar detalles de certificación

    Endpoints bajo estrés:
      - POST /api/method/lms.lms.doctype.lms_certificate.lms_certificate.create_certificate
        → Valida elegibilidad (DB read) + crea certificado (DB write) + email (RQ queue)
      - GET  /api/method/lms.lms.api.get_certification_details
        → Consulta estado de certificación
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

    @task(5)
    def request_certificate(self):
        idx = (self._user_index % 5) + 1
        course_title = f"Cert Stress Course {idx}"
        resp = self.client.post(
            "/api/method/lms.lms.doctype.lms_certificate.lms_certificate.create_certificate",
            json={"course": course_title},
            name="POST create_certificate",
        )
        if resp.status_code != 200:
            resp.failure(f"Certificate creation failed: {resp.text}")

    @task(1)
    def check_certification_details(self):
        idx = (self._user_index % 5) + 1
        course_title = f"Cert Stress Course {idx}"
        self.client.get(
            "/api/method/lms.lms.api.get_certification_details",
            params={"course": course_title},
            name="GET get_certification_details",
        )
