import itertools
from locust import HttpUser, task, between
from tests.stress.common.auth import get_student_credentials


class CertificateStressUser(HttpUser):
    """
    Solicitudes masivas de certificados.

    Endpoints:
      - POST /api/method/lms.lms.doctype.lms_certificate.lms_certificate.create_certificate
      - GET  /api/method/lms.lms.api.get_certification_details
      - GET  /api/method/lms.lms.api.get_chart_details
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

    @task(5)
    def request_certificate(self):
        if not self._logged_in:
            return
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
        if not self._logged_in:
            return
        idx = (self._idx % 5) + 1
        course_title = f"Cert Stress Course {idx}"
        self.client.get(
            "/api/method/lms.lms.api.get_certification_details",
            params={"course": course_title},
            name="GET get_certification_details",
        )

    @task(1)
    def get_chart_details(self):
        if not self._logged_in:
            return
        self.client.get(
            "/api/method/lms.lms.api.get_chart_details",
            name="GET get_chart_details",
        )
