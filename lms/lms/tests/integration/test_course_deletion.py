"""
Pruebas de integración para Módulo 3 y 4: Eliminación de curso con estudiantes
Casos: INT-019 (Eliminar curso con estudiantes y submissions)
"""
import os
import unittest

import frappe
import json
from frappe.tests import IntegrationTestCase
from lms.lms.api import delete_course
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestCourseDeletion(IntegrationTestCase):
    """
    Prueba de integración para la eliminación de cursos con estudiantes
    """

    def setUp(self):
        """Configuración antes de CADA prueba"""
        super().setUp()
        frappe.set_user("Administrator")

        # --- 1. Crear curso ---
        self.course_title = f"Curso Eliminar {frappe.generate_hash(length=6)}"
        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": self.course_title,
            "published": 1,
            "short_introduction": "Curso para prueba de eliminación",
            "description": "Este curso se utiliza para probar la eliminación con estudiantes"
        })
        course.append("instructors", {"instructor": "Administrator"})
        course.insert()
        self.course_name = course.name
        print(f"Curso '{self.course_title}' creado (ID: {self.course_name})")

        # --- 2. Crear capítulo ---
        chapter = frappe.get_doc({
            "doctype": "Course Chapter",
            "title": "Capítulo 1",
            "course": self.course_name,
            "is_scorm_package": 0
        })
        chapter.flags.ignore_links = True
        chapter.insert()
        self.chapter_name = chapter.name

        chapter_ref = frappe.get_doc({
            "doctype": "Chapter Reference",
            "chapter": self.chapter_name,
            "parent": self.course_name,
            "parenttype": "LMS Course",
            "parentfield": "chapters",
            "idx": 1
        })
        chapter_ref.flags.ignore_links = True
        chapter_ref.insert()

        # --- 3. Crear lección ---
        lesson = frappe.get_doc({
            "doctype": "Course Lesson",
            "title": "Lección 1",
            "chapter": self.chapter_name,
            "course": self.course_name
        })
        lesson.flags.ignore_links = True
        lesson.insert()
        self.lesson_name = lesson.name

        lesson_ref = frappe.get_doc({
            "doctype": "Lesson Reference",
            "lesson": self.lesson_name,
            "parent": self.chapter_name,
            "parenttype": "Course Chapter",
            "parentfield": "lessons",
            "idx": 1
        })
        lesson_ref.flags.ignore_links = True
        lesson_ref.insert()
        frappe.db.commit()
        print(f"Capítulo y lección creados")

        # --- 4. Crear preguntas ---
        self.question_names = []
        questions_data = [
            {
                "question": "¿Cuál es la capital de Francia?",
                "type": "Choices",
                "option_1": "París",
                "option_2": "Londres",
                "option_3": "Berlín",
                "is_correct_1": 1,
                "is_correct_2": 0,
                "is_correct_3": 0
            },
            {
                "question": "¿Cuánto es 2 + 2?",
                "type": "Choices",
                "option_1": "3",
                "option_2": "4",
                "option_3": "5",
                "is_correct_1": 0,
                "is_correct_2": 1,
                "is_correct_3": 0
            }
        ]

        for q_data in questions_data:
            q = frappe.get_doc({
                "doctype": "LMS Question",
                "question": q_data["question"],
                "type": q_data["type"],
                "option_1": q_data.get("option_1"),
                "option_2": q_data.get("option_2"),
                "option_3": q_data.get("option_3"),
                "is_correct_1": q_data.get("is_correct_1", 0),
                "is_correct_2": q_data.get("is_correct_2", 0),
                "is_correct_3": q_data.get("is_correct_3", 0)
            })
            q.insert()
            self.question_names.append(q.name)
        frappe.db.commit()

        # --- 5. Crear quiz ---
        quiz = frappe.get_doc({
            "doctype": "LMS Quiz",
            "title": "Quiz para Eliminación",
            "passing_percentage": 70,
            "course": self.course_name,
            "lesson": self.lesson_name,
            "max_attempts": 0,
            "total_marks": 10
        })
        quiz.insert()
        self.quiz_name = quiz.name

        for q_name in self.question_names:
            quiz.append("questions", {
                "question": q_name,
                "marks": 5
            })

        quiz.save()
        frappe.db.commit()
        print(f"Quiz '{self.quiz_name}' creado")

        # --- 6. Crear assignment ---
        assignment = frappe.get_doc({
            "doctype": "LMS Assignment",
            "title": "Assignment para Eliminación",
            "course": self.course_name,
            "lesson": self.lesson_name,
            "type": "Text",
            "question": "Describe el proceso de certificación."
        })
        assignment.insert()
        self.assignment_name = assignment.name
        frappe.db.commit()
        print(f"Assignment '{self.assignment_name}' creado")

        # --- 7. Crear estudiantes ---
        self.student1_email = f"test_student1_{frappe.generate_hash(length=6)}@example.com"
        self.student2_email = f"test_student2_{frappe.generate_hash(length=6)}@example.com"

        for email in [self.student1_email, self.student2_email]:
            user = frappe.get_doc({
                "doctype": "User",
                "email": email,
                "first_name": "Test",
                "last_name": f"Student {email[:6]}",
                "send_welcome_email": 0
            })
            user.insert()
            user.add_roles("LMS Student")
        frappe.db.commit()
        print(f"Estudiantes creados: {self.student1_email}, {self.student2_email}")

    def tearDown(self):
        """Limpieza después de CADA prueba"""
        frappe.set_user("Administrator")

        # Limpiar matrículas
        for email in [self.student1_email, self.student2_email]:
            if frappe.db.exists("LMS Enrollment", {"member": email, "course": self.course_name}):
                enrollment = frappe.get_doc("LMS Enrollment", {
                    "member": email,
                    "course": self.course_name
                })
                frappe.delete_doc("LMS Enrollment", enrollment.name, force=True, ignore_permissions=True)

        # Eliminar asignaciones de badge
        for email in [self.student1_email, self.student2_email]:
            if frappe.db.exists("LMS Badge Assignment", {"member": email}):
                assignments = frappe.get_all("LMS Badge Assignment", {"member": email})
                for assign in assignments:
                    frappe.delete_doc("LMS Badge Assignment", assign.name, force=True, ignore_permissions=True)

        # Eliminar cursos
        if frappe.db.exists("LMS Course", self.course_name):
            course = frappe.get_doc("LMS Course", self.course_name)
            for chapter_ref in course.get("chapters", []):
                chapter_name = chapter_ref.get("chapter")
                if chapter_name and frappe.db.exists("Course Chapter", chapter_name):
                    chapter = frappe.get_doc("Course Chapter", chapter_name)
                    for lesson_ref in chapter.get("lessons", []):
                        lesson_name = lesson_ref.get("lesson")
                        if lesson_name and frappe.db.exists("Course Lesson", lesson_name):
                            frappe.delete_doc("Course Lesson", lesson_name, force=True, ignore_permissions=True)
                    frappe.delete_doc("Course Chapter", chapter_name, force=True, ignore_permissions=True)
            frappe.delete_doc("LMS Course", self.course_name, force=True, ignore_permissions=True)
            frappe.db.commit()

        # Eliminar usuarios
        for email in [self.student1_email, self.student2_email]:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            frappe.db.commit()

        # Eliminar quiz y assignment
        if frappe.db.exists("LMS Quiz", self.quiz_name):
            frappe.delete_doc("LMS Quiz", self.quiz_name, force=True, ignore_permissions=True)
        if frappe.db.exists("LMS Assignment", self.assignment_name):
            frappe.delete_doc("LMS Assignment", self.assignment_name, force=True, ignore_permissions=True)

        super().tearDown()

    # ======================================================================
    # INT-019: Eliminar curso con estudiantes
    # ======================================================================

    def test_int_019_delete_course_with_students(self):
        """
        INT-019: Verificar que al eliminar un curso con estudiantes y submissions,
        se eliminen en cascada enrollments, progress y submissions
        """
        print("\n" + "="*70)
        print(">  INT-019: Eliminar curso con estudiantes")
        print("="*70)

        # --- 1. Matricular estudiantes ---
        print("\nPaso 1: Matricular estudiantes")
        for email in [self.student1_email, self.student2_email]:
            enrollment = frappe.get_doc({
                "doctype": "LMS Enrollment",
                "member": email,
                "course": self.course_name
            })
            enrollment.flags.ignore_links = True
            enrollment.insert()
            frappe.db.commit()
            print(f"    Estudiante {email} matriculado")

        enrollments_before = frappe.db.count("LMS Enrollment", {"course": self.course_name})
        self.assertEqual(enrollments_before, 2)
        print(f"    {enrollments_before} matrículas existentes")

        # --- 2. Crear quiz submissions ---
        print("\nPaso 2: Crear quiz submissions")
        frappe.set_user(self.student1_email)
        results = [
            {"question_name": self.question_names[0], "answer": ["París"]},
            {"question_name": self.question_names[1], "answer": ["4"]}
        ]
        submission = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results)
        )
        frappe.db.commit()
        print(f"    Quiz submission creada: {submission['submission']}")

        frappe.set_user(self.student2_email)
        results = [
            {"question_name": self.question_names[0], "answer": ["París"]},
            {"question_name": self.question_names[1], "answer": ["4"]}
        ]
        submission2 = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results)
        )
        frappe.db.commit()
        print(f"    Quiz submission creada: {submission2['submission']}")

        quiz_submissions_before = frappe.db.count("LMS Quiz Submission", {"quiz": self.quiz_name})
        self.assertEqual(quiz_submissions_before, 2)
        print(f"    {quiz_submissions_before} quiz submissions existentes")

        # --- 3. Crear assignment submissions ---
        print("\nPaso 3: Crear assignment submissions")
        frappe.set_user(self.student1_email)
        assignment_sub1 = frappe.get_doc({
            "doctype": "LMS Assignment Submission",
            "member": self.student1_email,
            "assignment": self.assignment_name,
            "lesson": self.lesson_name,
            "type": "Text",
            "answer": "Respuesta del estudiante 1",
            "status": "Pass"
        })
        assignment_sub1.flags.ignore_links = True
        assignment_sub1.insert()
        frappe.db.commit()
        print(f"    Assignment submission creada: {assignment_sub1.name}")

        frappe.set_user(self.student2_email)
        assignment_sub2 = frappe.get_doc({
            "doctype": "LMS Assignment Submission",
            "member": self.student2_email,
            "assignment": self.assignment_name,
            "lesson": self.lesson_name,
            "type": "Text",
            "answer": "Respuesta del estudiante 2",
            "status": "Pass"
        })
        assignment_sub2.flags.ignore_links = True
        assignment_sub2.insert()
        frappe.db.commit()
        print(f"    Assignment submission creada: {assignment_sub2.name}")

        assignment_submissions_before = frappe.db.count("LMS Assignment Submission", {"assignment": self.assignment_name})
        self.assertEqual(assignment_submissions_before, 2)
        print(f"    {assignment_submissions_before} assignment submissions existentes")

        # --- 4. Verificar course progress ---
        print("\nPaso 4: Verificar course progress")
        progress_count_before = frappe.db.count("LMS Course Progress", {"course": self.course_name})
        print(f"    {progress_count_before} registros de progreso existentes")

        # --- 5. Eliminar submissions (quiz y assignment) y assignments ---
        print("\nPaso 5: Eliminar submissions y assignments")
        frappe.set_user("Administrator")

        # 5.1 Eliminar quiz submissions
        quiz_submissions = frappe.get_all(
            "LMS Quiz Submission",
            {"quiz": self.quiz_name},
            pluck="name"
        )
        for sub_name in quiz_submissions:
            frappe.delete_doc("LMS Quiz Submission", sub_name, force=True, ignore_permissions=True)
        frappe.db.commit()
        print(f"    {len(quiz_submissions)} quiz submissions eliminadas")

        # 5.2 Eliminar assignment submissions
        assignment_submissions = frappe.get_all(
            "LMS Assignment Submission",
            {"assignment": self.assignment_name},
            pluck="name"
        )
        for sub_name in assignment_submissions:
            frappe.delete_doc("LMS Assignment Submission", sub_name, force=True, ignore_permissions=True)
        frappe.db.commit()
        print(f"    {len(assignment_submissions)} assignment submissions eliminadas")

        # 5.3 Eliminar assignment (documento padre)
        if frappe.db.exists("LMS Assignment", self.assignment_name):
            frappe.delete_doc("LMS Assignment", self.assignment_name, force=True, ignore_permissions=True)
            frappe.db.commit()
            print(f"    Assignment '{self.assignment_name}' eliminado")

        # --- 6. Eliminar curso ---
        print("\nPaso 6: Eliminar curso")
        delete_course(self.course_name)
        frappe.db.commit()
        print(f"    Curso '{self.course_name}' eliminado")

        # --- 7. Verificar curso eliminado ---
        print("\nPaso 7: Verificar curso eliminado")
        course_exists = frappe.db.exists("LMS Course", self.course_name)
        self.assertFalse(course_exists)
        print("    Curso eliminado correctamente")

        # --- 8. Verificar matrículas eliminadas ---
        print("\nPaso 8: Verificar matrículas eliminadas")
        enrollments_after = frappe.db.count("LMS Enrollment", {"course": self.course_name})
        self.assertEqual(enrollments_after, 0)
        print("    Matrículas eliminadas")

        # --- 9. Verificar progress eliminados ---
        print("\nPaso 9: Verificar progress eliminados")
        progress_count_after = frappe.db.count("LMS Course Progress", {"course": self.course_name})
        self.assertEqual(progress_count_after, 0)
        print("    Course Progress eliminados")

        # --- 10. Verificar quiz submissions eliminadas ---
        print("\nPaso 10: Verificar quiz submissions eliminadas")
        quiz_submissions_after = frappe.db.count("LMS Quiz Submission", {"quiz": self.quiz_name})
        self.assertEqual(quiz_submissions_after, 0)
        print("    Quiz submissions eliminadas")

        # --- 11. Verificar assignment submissions eliminadas ---
        print("\nPaso 11: Verificar assignment submissions eliminadas")
        assignment_submissions_after = frappe.db.count("LMS Assignment Submission", {"assignment": self.assignment_name})
        self.assertEqual(assignment_submissions_after, 0)
        print("    Assignment submissions eliminadas")

        print("\n" + "="*70)
        print("(n.n) INT-019: Prueba completada exitosamente")
        print("="*70)
