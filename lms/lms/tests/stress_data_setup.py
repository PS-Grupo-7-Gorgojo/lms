"""Data seeding module for stress tests.

Run via bench in CI:
    bench --site frappe.local execute lms.lms.tests.stress_data_setup.seed_enrollment_data

This creates the users and courses needed by Locust scenarios.
"""

import frappe
from frappe.utils.password import update_password

USER_PASSWORD = "stress123"
STUDENT_COUNT = 50


def seed_enrollment_data(course_count=5, student_count=None):
    """Create test users and courses for enrollment stress tests."""
    if student_count is None:
        student_count = STUDENT_COUNT

    courses = _create_stress_courses(course_count)
    students = _create_stress_students(student_count)

    frappe.db.commit()
    return {
        "courses": courses,
        "students": students,
        "password": USER_PASSWORD,
    }


def _create_stress_courses(count):
    created = []
    if not frappe.db.exists("User", "stress_instructor@test.com"):
        instructor = frappe.new_doc("User")
        instructor.update({
            "email": "stress_instructor@test.com",
            "first_name": "Stress",
            "last_name": "Instructor",
            "send_welcome_email": 0,
        })
        instructor.append("roles", {"role": "Course Creator"})
        instructor.save(ignore_permissions=True)
        update_password("stress_instructor@test.com", USER_PASSWORD)

    for i in range(count):
        title = f"Stress Course {i + 1}"
        if frappe.db.exists("LMS Course", {"title": title}):
            created.append(title)
            continue

        course = frappe.new_doc("LMS Course")
        course.update({
            "title": title,
            "short_introduction": f"Stress test course #{i + 1}",
            "description": f"Auto-generated course for enrollment stress testing.",
            "published": 1,
            "upcoming": 0,
            "disable_self_enrollment": 0,
        })
        course.save(ignore_permissions=True)
        created.append(title)

    return created


def _create_stress_students(count):
    created = []
    for i in range(count):
        email = f"stress_student{i + 1}@test.com"
        if frappe.db.exists("User", email):
            created.append(email)
            continue

        user = frappe.new_doc("User")
        user.update({
            "email": email,
            "first_name": f"Stress{i + 1}",
            "last_name": "Student",
            "send_welcome_email": 0,
        })
        user.save(ignore_permissions=True)
        update_password(email, USER_PASSWORD)
        created.append(email)

    return created
