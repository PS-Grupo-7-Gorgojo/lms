import itertools
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
      - GET  /api/method/lms.lms.api.get_certification_details
    """
    wait_time = between(0, 1)
    _counter = itertools.count(1)

    def on_start(self):
        self._idx = next(self.__class__._counter)
        email, password = get_student_credentials(self._idx)
        with self.client.post(
            "/api/method/login",
            json={"usr": email, "pwd": password},
            catch_response=True,
            name="POST /api/method/login",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Login failed ({resp.status_code})")

    @task(5)
    def request_certificate(self):
        idx = (self._idx % 5) + 1
        course_title = f"Cert Stress Course {idx}"
        with self.client.post(
            "/api/method/lms.lms.doctype.lms_certificate.lms_certificate.create_certificate",
            json={"course": course_title},
            catch_response=True,
            name="POST create_certificate",
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Cert failed ({resp.status_code})")

    @task(1)
    def check_certification_details(self):
        idx = (self._idx % 5) + 1
        course_title = f"Cert Stress Course {idx}"
        self.client.get(
            "/api/method/lms.lms.api.get_certification_details",
            params={"course": course_title},
            name="GET get_certification_details",
        )
