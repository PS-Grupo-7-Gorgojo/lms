import os
from urllib.parse import urljoin


class FrappeAuth:
    """
    Handles authentication against a Frappe site via /api/method/login.
    Stores session cookies for subsequent requests.
    """

    def __init__(self, host: str, username: str, password: str):
        self.host = host.rstrip("/")
        self.username = username
        self.password = password

    def login(self, client):
        response = client.post(
            "/api/method/login",
            json={"usr": self.username, "pwd": self.password},
            name="POST /api/method/login",
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Login failed for {self.username}: {response.status_code} {response.text}"
            )
        return response

    @staticmethod
    def login_as(client, username, password):
        client.post(
            "/api/method/login",
            json={"usr": username, "pwd": password},
            name="POST /api/method/login",
        )


def get_student_credentials(idx: int):
    max_students = int(os.getenv("STRESS_STUDENT_MAX", "50"))
    wrapped = ((idx - 1) % max_students) + 1
    email = os.getenv(
        "STRESS_STUDENT_EMAIL_TEMPLATE",
        "stress_student{}@test.com",
    ).format(wrapped)
    password = os.getenv("STRESS_STUDENT_PASSWORD", "stress123")
    return email, password
