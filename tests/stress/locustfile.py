"""
Locust entry point for LMS stress tests.

Usage:
    # Web UI (http://localhost:8089)
    locust -f tests/stress/locustfile.py --host=http://lms.test:8000

    # Headless with scenario selection (CI)
    SCENARIO=enrollment locust -f tests/stress/locustfile.py --headless \
        -u 200 -r 50 -t 120s --host=http://lms.test:8000 \
        --csv=reports/stress --html=reports/stress.html

Scenarios:
    - enrollment       : Ráfagas de inscripciones concurrentes
    - certificate      : Solicitudes masivas de certificados
    - quiz_submission  : Entregas simultáneas de quizzes
    - course_access    : Acceso concurrente a cursos y evaluaciones (TODO)
    - redis_queue      : Saturación de colas Redis/RQ (TODO)
"""

import os

from locust import events
from tests.stress.scenarios.enrollment import EnrollmentStressUser
from tests.stress.scenarios.certificate import CertificateStressUser
from tests.stress.scenarios.quiz_submission import QuizSubmissionStressUser

_SCENARIO_MAP = {
    "enrollment": EnrollmentStressUser,
    "certificate": CertificateStressUser,
    "quiz_submission": QuizSubmissionStressUser,
}

user_classes = list(_SCENARIO_MAP.values())


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    scenario = os.getenv("SCENARIO", "")
    if scenario and scenario in _SCENARIO_MAP:
        environment.user_classes = [_SCENARIO_MAP[scenario]]
    else:
        environment.user_classes = list(_SCENARIO_MAP.values())
    environment.runner.stats.reset_all()
