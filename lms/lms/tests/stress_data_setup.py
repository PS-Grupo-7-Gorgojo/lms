"""Data seeding module for stress tests.

Run via bench in CI:
    bench --site lms.test execute lms.lms.tests.stress_data_setup.seed_enrollment_data
    bench --site lms.test execute lms.lms.tests.stress_data_setup.seed_certificate_data
"""

import frappe
from frappe.utils.password import update_password
from frappe.utils import nowdate

USER_PASSWORD = "stress123"
STUDENT_COUNT = 50
CERT_STUDENT_COUNT = 30


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


def seed_certificate_data(course_count=5, student_count=None):
    """Create courses with lessons, enrollments at 100% for certificate stress tests."""
    if student_count is None:
        student_count = CERT_STUDENT_COUNT

    students = _create_stress_students(student_count)
    courses = _create_cert_courses(course_count)
    _complete_enrollments(courses, students[:student_count])

    frappe.db.commit()
    return {
        "courses": courses,
        "students": students[:student_count],
        "password": USER_PASSWORD,
    }


def _create_stress_courses(count):
    created = []
    _ensure_instructor()

    for i in range(count):
        title = f"Stress Course {i + 1}"
        if frappe.db.exists("LMS Course", {"title": title}):
            created.append(title)
            continue

        course = frappe.new_doc("LMS Course")
        course.update({
            "title": title,
            "short_introduction": f"Stress test course #{i + 1}",
            "description": "Auto-generated course for enrollment stress testing.",
            "published": 1,
            "upcoming": 0,
            "disable_self_enrollment": 0,
            "instructors": [{"instructor": "stress_instructor@test.com"}],
        })
        course.save(ignore_permissions=True)
        created.append(title)

    return created


def _create_cert_courses(count):
    """Create courses with enable_certification=1, chapters, and lessons."""
    created = []
    _ensure_instructor()

    for i in range(count):
        title = f"Cert Stress Course {i + 1}"
        if frappe.db.exists("LMS Course", {"title": title}):
            created.append(title)
            continue

        course = frappe.new_doc("LMS Course")
        course.update({
            "title": title,
            "short_introduction": f"Certificate stress course #{i + 1}",
            "description": "Auto-generated course for certificate stress testing.",
            "published": 1,
            "upcoming": 0,
            "disable_self_enrollment": 0,
            "enable_certification": 1,
            "instructors": [{"instructor": "stress_instructor@test.com"}],
        })
        course.save(ignore_permissions=True)

        chapter = _create_chapter(title, course.name)
        _create_lesson(f"Lesson 1 - {title}", chapter.name, course.name)
        _create_lesson(f"Lesson 2 - {title}", chapter.name, course.name)

        created.append(title)

    return created


def _ensure_instructor():
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


def _create_chapter(course_title, course_name):
    chapter = frappe.new_doc("Course Chapter")
    chapter.update({
        "title": f"Chapter - {course_title}",
        "course": course_name,
        "is_scorm_package": 0,
    })
    chapter.save(ignore_permissions=True)

    chapter_ref = frappe.new_doc("Chapter Reference")
    chapter_ref.update({
        "chapter": chapter.name,
        "parent": course_name,
        "parenttype": "LMS Course",
        "parentfield": "chapters",
        "idx": 1,
    })
    chapter_ref.save(ignore_permissions=True)
    return chapter


def _create_lesson(lesson_title, chapter_name, course_name):
    lesson = frappe.new_doc("Course Lesson")
    lesson.update({
        "title": lesson_title,
        "chapter": chapter_name,
        "course": course_name,
    })
    lesson.save(ignore_permissions=True)

    lesson_ref = frappe.new_doc("Lesson Reference")
    lesson_ref.update({
        "lesson": lesson.name,
        "parent": chapter_name,
        "parenttype": "Course Chapter",
        "parentfield": "lessons",
        "idx": 1,
    })
    lesson_ref.save(ignore_permissions=True)
    return lesson


def _complete_enrollments(courses, students):
    """Create enrollments with 100% progress for each student in each course."""
    for student in students:
        for course_title in courses:
            course_name = frappe.db.get_value("LMS Course", {"title": course_title}, "name")
            if not course_name:
                continue

            existing = frappe.db.exists("LMS Enrollment", {
                "member": student,
                "course": course_name,
            })
            if existing:
                frappe.db.set_value("LMS Enrollment", existing, "progress", 100)
                continue

            enrollment = frappe.new_doc("LMS Enrollment")
            enrollment.update({
                "member": student,
                "course": course_name,
                "progress": 100,
            })
            enrollment.save(ignore_permissions=True)


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
