"""Data seeding module for stress tests.

Run via bench in CI:
    bench --site lms.test execute lms.lms.tests.stress_data_setup.seed_enrollment_data
    bench --site lms.test execute lms.lms.tests.stress_data_setup.seed_certificate_data
"""

import json
import os

import frappe
from frappe.utils.password import update_password
from frappe.utils import nowdate

USER_PASSWORD = "stress123"
STUDENT_COUNT = 50
CERT_STUDENT_COUNT = 30


def reset_login_trackers():
    """Clear Redis login attempt trackers so stress tests don't lock accounts."""
    cache = frappe.cache()
    cache.delete_keys("*login_attempt*")
    frappe.db.commit()


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


QUIZ_COURSE_COUNT = 3
QUIZ_STUDENT_COUNT = 30
QUESTIONS_PER_QUIZ = 5

_QUIZ_QUESTIONS_CACHE = {}


def seed_quiz_data(course_count=None, student_count=None):
    """Create courses with quizzes and questions for quiz submission stress tests."""
    if course_count is None:
        course_count = QUIZ_COURSE_COUNT
    if student_count is None:
        student_count = QUIZ_STUDENT_COUNT

    students = _create_stress_students(student_count)
    courses = _create_quiz_courses(course_count)
    for student in students[:student_count]:
        for course_title in courses:
            course_name = frappe.db.get_value("LMS Course", {"title": course_title}, "name")
            if course_name and not frappe.db.exists(
                "LMS Enrollment", {"member": student, "course": course_name}
            ):
                enrollment = frappe.new_doc("LMS Enrollment")
                enrollment.update({"member": student, "course": course_name})
                enrollment.save(ignore_permissions=True)

    frappe.db.commit()
    _populate_quiz_cache()
    _write_quiz_fixture(_QUIZ_QUESTIONS_CACHE)
    quizzes = list(_QUIZ_QUESTIONS_CACHE.keys())
    return {"courses": courses, "students": students, "quizzes": quizzes, "password": USER_PASSWORD}


def _populate_quiz_cache():
    for quiz_name in list(_QUIZ_QUESTIONS_CACHE.keys()):
        _QUIZ_QUESTIONS_CACHE[quiz_name] = _get_question_names(quiz_name)


def _create_quiz_courses(count):
    created = []
    _ensure_instructor()
    for i in range(count):
        title = f"Quiz Stress Course {i + 1}"
        if frappe.db.exists("LMS Course", {"title": title}):
            created.append(title)
            continue
        course = frappe.new_doc("LMS Course")
        course.update({
            "title": title,
            "short_introduction": f"Quiz stress course #{i + 1}",
            "description": "Auto-generated course for quiz submission stress testing.",
            "published": 1,
            "upcoming": 0,
            "disable_self_enrollment": 0,
            "instructors": [{"instructor": "stress_instructor@test.com"}],
        })
        course.save(ignore_permissions=True)

        chapter = _create_chapter(title, course.name)
        lesson = _create_lesson(f"Lesson 1 - {title}", chapter.name, course.name)
        quiz = _create_quiz(f"Quiz - {title}", lesson.name, course.name)
        _QUIZ_QUESTIONS_CACHE[quiz] = []

        created.append(title)
    return created


def _create_questions(count):
    questions = []
    for i in range(count):
        title = f"Stress Question {frappe.generate_hash(length=6)}"
        existing = frappe.db.exists("LMS Question", {"question": title})
        if existing:
            questions.append(frappe.get_doc("LMS Question", existing))
            continue
        q = frappe.new_doc("LMS Question")
        q.update({
            "question": title,
            "type": "Choices",
            "option_1": "Correct Answer",
            "is_correct_1": 1,
            "option_2": "Wrong Answer A",
            "is_correct_2": 0,
            "option_3": "Wrong Answer B",
            "is_correct_3": 0,
            "option_4": "Wrong Answer C",
            "is_correct_4": 0,
        })
        q.save(ignore_permissions=True)
        questions.append(q)
    return questions


def _create_quiz(quiz_title, lesson_name, course_name):
    existing = frappe.db.exists("LMS Quiz", {"title": quiz_title})
    if existing:
        return existing

    questions = _create_questions(QUESTIONS_PER_QUIZ)
    quiz = frappe.new_doc("LMS Quiz")
    quiz.update({
        "title": quiz_title,
        "lesson": lesson_name,
        "course": course_name,
        "passing_percentage": 50,
        "max_attempts": 0,
    })
    for q in questions:
        quiz.append("questions", {"question": q.name, "marks": 2})
    quiz.save(ignore_permissions=True)
    return quiz.name


def _get_question_names(quiz_name):
    rows = frappe.get_all(
        "LMS Quiz Question",
        {"parent": quiz_name},
        ["question", "marks"],
    )
    return [{"name": r.question, "marks": r.marks} for r in rows]


def _create_stress_students(count):
    created = []
    for i in range(count):
        email = f"stress_student{i + 1}@test.com"
        if frappe.db.exists("User", email):
            if not frappe.db.exists("Has Role", {"parent": email, "role": "LMS Student"}):
                user_doc = frappe.get_doc("User", email)
                user_doc.append("roles", {"role": "LMS Student"})
                user_doc.save(ignore_permissions=True)
            created.append(email)
            continue

        user = frappe.new_doc("User")
        user.update({
            "email": email,
            "first_name": f"Stress{i + 1}",
            "last_name": "Student",
            "send_welcome_email": 0,
        })
        user.append("roles", {"role": "LMS Student"})
        user.save(ignore_permissions=True)
        update_password(email, USER_PASSWORD)
        created.append(email)

    return created


REDIS_STUDENT_COUNT = 40


def seed_redis_queue_data(course_count=4, student_count=None):
    """Create data for Redis/RQ saturation: courses with lessons, quizzes, certs enabled."""
    if student_count is None:
        student_count = REDIS_STUDENT_COUNT

    students = _create_stress_students(student_count)
    _ensure_instructor()

    titles = []
    for i in range(course_count):
        title = f"Redis Stress Course {i + 1}"
        if frappe.db.exists("LMS Course", {"title": title}):
            titles.append(title)
            continue

        course = frappe.new_doc("LMS Course")
        course.update({
            "title": title,
            "short_introduction": f"Redis stress course #{i + 1}",
            "description": "Auto-generated for Redis/RQ saturation testing.",
            "published": 1,
            "upcoming": 0,
            "disable_self_enrollment": 0,
            "enable_certification": 1,
            "instructors": [{"instructor": "stress_instructor@test.com"}],
        })
        course.save(ignore_permissions=True)

        chapter = _create_chapter(title, course.name)
        lesson = _create_lesson(f"Lesson 1 - {title}", chapter.name, course.name)
        _QUIZ_QUESTIONS_CACHE[_create_quiz(f"RQ Quiz - {title}", lesson.name, course.name)] = []

        for student in students[:student_count]:
            if not frappe.db.exists("LMS Enrollment", {"member": student, "course": course.name}):
                enrollment = frappe.new_doc("LMS Enrollment")
                enrollment.update({"member": student, "course": course.name, "progress": 100})
                enrollment.save(ignore_permissions=True)

        titles.append(title)

    frappe.db.commit()
    _populate_quiz_cache()
    _write_quiz_fixture(_QUIZ_QUESTIONS_CACHE)
    return {"courses": titles, "students": students, "password": USER_PASSWORD}


def _write_quiz_fixture(cache):
    app_path = frappe.get_app_path("lms")
    fixture_dir = os.path.join(app_path, "tests", "stress", "fixtures")
    os.makedirs(fixture_dir, exist_ok=True)
    filepath = os.path.join(fixture_dir, "quiz_data.json")
    data = {}
    for quiz_name in cache:
        quiz_title = frappe.db.get_value("LMS Quiz", quiz_name, "title")
        if not quiz_title:
            continue
        data[quiz_title] = {
            "name": quiz_name,
            "questions": _get_question_names(quiz_name),
        }
    with open(filepath, "w") as f:
        json.dump(data, f)
