"""
Locust entry point for LMS stress tests.

Usage:
    # Web UI (http://localhost:8089)
    locust -f tests/stress/locustfile.py --host=http://lms.test:8000

    # Headless (CI)
    locust -f tests/stress/locustfile.py --headless \
        -u 200 -r 50 -t 120s \
        --host=http://lms.test:8000 \
        --csv=reports/stress \
        --html=reports/stress.html

Scenarios available:
    - enrollment       : Ráfagas de inscripciones concurrentes
    - certificate      : Solicitudes masivas de certificados (TODO)
    - quiz_submission  : Entregas simultáneas de quizzes (TODO)
    - course_access    : Acceso concurrente a cursos y evaluaciones (TODO)
    - redis_queue      : Saturación de colas Redis/RQ (TODO)
"""

from locust import events
from tests.stress.scenarios.enrollment import EnrollmentStressUser


@events.init.add_listener
def on_locust_init(environment, **kwargs):
    if environment.shape_class:
        return
    environment.runner.stats.reset_all()
