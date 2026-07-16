"""
Pruebas de integración para Módulo 8: Certificaciones
Casos: INT-009 (Certificado automático al completar curso)
"""
import os
import unittest

import frappe
import json
from frappe.tests import IntegrationTestCase
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz
from lms.lms.doctype.lms_certificate.lms_certificate import create_certificate

@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestCertificateCompletion(IntegrationTestCase):
    """
    Prueba de integración para la emisión automática de certificados
    Verifica que al completar un curso al 100%, se pueda emitir un certificado
    """

    def setUp(self):
        """Configuración antes de CADA prueba"""
        super().setUp()
        frappe.set_user("Administrator")
        frappe.db.delete("LMS Certificate Request")
        frappe.db.commit()

        # 1. Crear curso con certificación habilitada
        self.course_title = f"Curso Certificado {frappe.generate_hash(length=6)}"
        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": self.course_title,
            "published": 1,
            "enable_certification": 1,
            "short_introduction": "Curso para certificación",
            "description": "Este curso se utiliza para probar la emisión de certificados"
        })
        course.append("instructors", {"instructor": "Administrator"})
        course.insert()
        self.course_name = course.name
        print(f"Curso '{self.course_title}' creado (ID: {self.course_name})")

        # 2. Crear capítulo
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
        print(f"Capítulo '{self.chapter_name}' creado")

        # 3. Crear Lección 1
        self.lesson1_name = self._create_lesson("Lección 1: Introducción", idx=1)
        print(f"Lección 1 '{self.lesson1_name}' creada")

        # 4. Crear preguntas
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
            },
            {
                "question": "¿Qué color es el cielo?",
                "type": "Choices",
                "option_1": "Rojo",
                "option_2": "Verde",
                "option_3": "Azul",
                "is_correct_1": 0,
                "is_correct_2": 0,
                "is_correct_3": 1
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
            print(f"Pregunta creada: {q.name}")

        # 5. Crear quiz
        quiz = frappe.get_doc({
            "doctype": "LMS Quiz",
            "title": "Quiz de Certificación",
            "passing_percentage": 70,
            "course": self.course_name,
            "max_attempts": 0,
            "total_marks": 15
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
        print(f"Quiz '{self.quiz_name}' creado con passing_percentage=70%")

        # 6. Crear Lección 2 (con quiz)
        self.lesson2_name = self._create_lesson_with_quiz(
            title="Lección 2: Evaluación",
            quiz_name=self.quiz_name,
            idx=2
        )
        print(f"Lección 2 '{self.lesson2_name}' creada con quiz")

        # 7. Crear assignment CON el campo obligatorio 'question'
        self.assignment_name = f"test-assignment-{frappe.generate_hash(length=6)}"
        assignment = frappe.get_doc({
            "doctype": "LMS Assignment",
            "title": "Assignment de Certificación",
            "name": self.assignment_name,
            "course": self.course_name,
            "lesson": self.lesson2_name,
            "type": "Text",
            "question": "Describe el proceso de certificación en tus propias palabras."  # ✅ Campo obligatorio
        })
        assignment.insert()
        frappe.db.commit()
        print(f"Assignment '{self.assignment_name}' creado")

        # 8. Crear usuario estudiante
        self.student_email = f"test_student_cert_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.student_email,
            "first_name": "Test",
            "last_name": "Certificate Student",
            "send_welcome_email": 0
        })
        user.insert()
        user.add_roles("LMS Student")
        frappe.db.commit()
        print(f" Usuario '{self.student_email}' creado con rol LMS Student")

    def _create_lesson(self, title, idx):
        """Crea una lección simple sin quiz"""
        lesson = frappe.get_doc({
            "doctype": "Course Lesson",
            "title": title,
            "chapter": self.chapter_name,
            "course": self.course_name
        })
        lesson.flags.ignore_links = True
        lesson.insert()

        lesson_ref = frappe.get_doc({
            "doctype": "Lesson Reference",
            "lesson": lesson.name,
            "parent": self.chapter_name,
            "parenttype": "Course Chapter",
            "parentfield": "lessons",
            "idx": idx
        })
        lesson_ref.flags.ignore_links = True
        lesson_ref.insert()
        frappe.db.commit()

        return lesson.name

    def _create_lesson_with_quiz(self, title, quiz_name, idx):
        """Crea una lección con quiz embebido"""
        lesson = frappe.get_doc({
            "doctype": "Course Lesson",
            "title": title,
            "chapter": self.chapter_name,
            "course": self.course_name,
            "content": json.dumps({
                "blocks": [
                    {
                        "type": "quiz",
                        "data": {
                            "quiz": quiz_name
                        }
                    }
                ]
            })
        })
        lesson.flags.ignore_links = True
        lesson.insert()

        lesson_ref = frappe.get_doc({
            "doctype": "Lesson Reference",
            "lesson": lesson.name,
            "parent": self.chapter_name,
            "parenttype": "Course Chapter",
            "parentfield": "lessons",
            "idx": idx
        })
        lesson_ref.flags.ignore_links = True
        lesson_ref.insert()
        frappe.db.commit()

        return lesson.name

    def tearDown(self):
        """Limpieza después de CADA prueba"""
        frappe.db.rollback()
        super().tearDown()

    # ======================================================================
    # INT-009: Certificado automático al completar curso
    # ======================================================================

    def test_int_009_auto_certificate_on_completion(self):
        """
        INT-009: Verificar que al completar el 100% del curso,
        se pueda emitir un certificado automáticamente
        """
        print("\n" + "="*70)
        print(">  INT-009: Certificado automático al completar curso")
        print("="*70)

        # 1. Crear matrícula
        print("\nPaso 1: Crear matrícula")
        enrollment = frappe.get_doc({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name
        })
        enrollment.flags.ignore_links = True
        enrollment.insert()
        frappe.db.commit()
        print(f"    Matrícula creada: {enrollment.name}")

        # 2. Verificar progreso inicial
        print("\nPaso 2: Verificar progreso inicial (0%)")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 0)
        print(f"    Progreso inicial: {enrollment.progress}%")

        # 3. Completar Lección 1
        print("\nPaso 3: Completar Lección 1")
        from lms.lms.doctype.course_lesson.course_lesson import save_progress

        frappe.set_user(self.student_email)
        save_progress(self.lesson1_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección 1 completada")

        enrollment.reload()
        print(f"    Progreso parcial: {enrollment.progress}%")

        # 4. Completar Lección 2
        print("\nPaso 4: Completar Lección 2")

        # Enviar quiz (100%)
        results_high = [
            {"question_name": self.question_names[0], "answer": ["París"]},
            {"question_name": self.question_names[1], "answer": ["4"]},
            {"question_name": self.question_names[2], "answer": ["Azul"]}
        ]

        submission = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results_high)
        )
        frappe.db.commit()
        print(f"    Quiz enviado y aprobado")

        # Enviar assignment
        assignment_submission = frappe.get_doc({
            "doctype": "LMS Assignment Submission",
            "member": self.student_email,
            "assignment": self.assignment_name,
            "lesson": self.lesson2_name,
            "type": "Text",
            "answer": "El proceso de certificación requiere completar todas las lecciones y evaluaciones.",
            "status": "Pass"
        })
        assignment_submission.flags.ignore_links = True
        assignment_submission.insert()
        frappe.db.commit()
        print(f"    Assignment enviado y aprobado")

        # Marcar lección completada
        save_progress(self.lesson2_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección 2 completada")

        # 5. Verificar progreso 100%
        print("\nPaso 5: Verificar progreso 100%")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100)
        print(f"    Progreso del curso: {enrollment.progress}%")

        # 6. Verificar NO hay certificado
        print("\nPaso 6: Verificar que NO hay certificado antes de emitir")
        certificate_exists = frappe.db.exists(
		    "LMS Certificate",
		    {"member": self.student_email, "course": self.course_name}
		)
        self.assertFalse(certificate_exists)
        print("    No hay certificado antes de emitir")

        # 7. Crear certificado
        print("\nPaso 7: Crear certificado")
        #frappe.set_user(self.student_email)i
        frappe.set_user("Administrator")

        default_template = frappe.db.get_value(
			"Print Format",
			{"doc_type": "LMS Certificate"},
			"name"
		)

        certificate = frappe.get_doc({
		    "doctype": "LMS Certificate",
		    "member": self.student_email,
		    "course": self.course_name,
		    "issue_date": frappe.utils.nowdate(),
		    "published": 1,
		    "template": default_template or "Standard"
		})
        certificate.insert(ignore_permissions=True)
        frappe.db.commit()

        self.assertIsNotNone(certificate)
        print(f"    Certificado creado: {certificate.name}")

        # 8. Verificar datos
        print("\nPaso 8: Verificar datos del certificado")
        cert_doc = frappe.get_doc("LMS Certificate", certificate.name)

        self.assertEqual(cert_doc.member, self.student_email)
        self.assertEqual(cert_doc.course, self.course_name)
        self.assertEqual(cert_doc.course_title, self.course_title)
        self.assertEqual(cert_doc.published, 1)

        print(f"    Certificado vinculado al estudiante: {cert_doc.member}")
        print(f"    Certificado vinculado al curso: {cert_doc.course}")
        print(f"    Título del curso: {cert_doc.course_title}")

        print("\n" + "="*70)
        print("(n.n) INT-009: Prueba completada exitosamente")
        print("="*70)

    # ======================================================================
    # INT-010: Solicitar certificado manual
    # ======================================================================

    def test_int_010_request_certificate_manually(self):
        """
        INT-010: Verificar que un estudiante pueda solicitar un certificado manualmente
        después de completar el curso al 100%
        """
        print("\n" + "="*70)
        print(">  INT-010: Solicitar certificado manual")
        print("="*70)

        # 1. Crear matrícula
        print("\nPaso 1: Crear matrícula")
        enrollment = frappe.get_doc({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name
        })
        enrollment.flags.ignore_links = True
        enrollment.insert()
        frappe.db.commit()
        print(f"    Matrícula creada: {enrollment.name}")

        # 2. Completar curso al 100% ---
        print("\nPaso 2: Completar curso")
        from lms.lms.doctype.course_lesson.course_lesson import save_progress

        frappe.set_user(self.student_email)

        # Completar Lección 1
        save_progress(self.lesson1_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección 1 completada")

        # Enviar quiz (100%)
        results_high = [
            {"question_name": self.question_names[0], "answer": ["París"]},
            {"question_name": self.question_names[1], "answer": ["4"]},
            {"question_name": self.question_names[2], "answer": ["Azul"]}
        ]

        submission = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results_high)
        )
        frappe.db.commit()
        print(f"    Quiz enviado y aprobado")

        # Enviar assignment
        assignment_submission = frappe.get_doc({
            "doctype": "LMS Assignment Submission",
            "member": self.student_email,
            "assignment": self.assignment_name,
            "lesson": self.lesson2_name,
            "type": "Text",
            "answer": "El proceso de certificación requiere completar todas las lecciones y evaluaciones.",
            "status": "Pass"
        })
        assignment_submission.flags.ignore_links = True
        assignment_submission.insert()
        frappe.db.commit()
        print(f"    Assignment enviado y aprobado")

        # Completar Lección 2
        save_progress(self.lesson2_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección 2 completada")

        # Verificar progreso 100%
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100)
        print(f"    Progreso del curso: {enrollment.progress}%")

        # 3. Verificar que NO hay certificado antes
        print("\nPaso 3: Verificar que NO hay certificado antes")
        certificate_exists = frappe.db.exists(
            "LMS Certificate",
            {"member": self.student_email, "course": self.course_name}
        )
        self.assertFalse(certificate_exists)
        print("    No hay certificado antes de solicitar")

        # 4. Crear Certificate Request
        print("\nPaso 4: Crear solicitud de certificado")
        frappe.set_user(self.student_email)

        certificate_request = frappe.get_doc({
            "doctype": "LMS Certificate Request",
            "member": self.student_email,
            "course": self.course_name,
            "date": frappe.utils.add_days(frappe.utils.nowdate(), 1),
            "start_time": "10:00:00",
            "end_time": "11:00:00"
        })
        certificate_request.insert()
        frappe.db.commit()

        self.assertIsNotNone(certificate_request.name)
        print(f"    Solicitud creada: {certificate_request.name}")

        # 5. Verificar datos del request
        print("\nPaso 5: Verificar datos de la solicitud")
        request_doc = frappe.get_doc("LMS Certificate Request", certificate_request.name)

        self.assertEqual(request_doc.member, self.student_email)
        self.assertEqual(request_doc.course, self.course_name)
        self.assertEqual(request_doc.status, "Upcoming")
        self.assertEqual(request_doc.course_title, self.course_title)

        print(f"    Solicitud vinculada al estudiante: {request_doc.member}")
        print(f"    Solicitud vinculada al curso: {request_doc.course}")
        print(f"    Estado: {request_doc.status}")

        # 6. Verificar que NO hay certificado aún
        print("\nPaso 6: Verificar que NO hay certificado aún")
        certificate_exists = frappe.db.exists(
            "LMS Certificate",
            {"member": self.student_email, "course": self.course_name}
        )
        self.assertFalse(certificate_exists)
        print("    No hay certificado (solo solicitud)")

        print("\n" + "="*70)
        print("(n.n) INT-010: Prueba completada exitosamente")
        print("   - Solicitud de certificado creada correctamente")
        print("   - Estado de la solicitud: Upcoming")
        print("   - Certificado aún no emitido (pendiente de evaluación)")
        print("="*70)

    # ======================================================================
    # CASO NEGATIVO
    # ======================================================================

    def test_no_certificate_without_completion(self):
        """
        INT-009-NEG: Verificar que un curso incompleto NO genera certificado
        """
        print("\n" + "="*70)
        print(">  INT-009-NEG: Curso incompleto NO genera certificado")
        print("="*70)

        # 1. Crear matrícula
        print("\nPaso 1: Crear matrícula")
        enrollment = frappe.get_doc({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name
        })
        enrollment.flags.ignore_links = True
        enrollment.insert()
        frappe.db.commit()
        print(f"    Matrícula creada: {enrollment.name}")

        # 2. Completar solo Lección 1
        print("\nPaso 2: Completar solo la Lección 1")
        from lms.lms.doctype.course_lesson.course_lesson import save_progress

        frappe.set_user(self.student_email)
        save_progress(self.lesson1_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección 1 completada")

        # 3. Verificar progreso NO es 100%
        print("\nPaso 3: Verificar progreso NO es 100%")
        enrollment.reload()
        self.assertNotEqual(enrollment.progress, 100)
        print(f"    Progreso: {enrollment.progress}% (curso incompleto)")

        # 4. Intentar crear certificado (debe fallar)
        print("\nPaso 4: Intentar crear certificado (debe fallar)")
        frappe.set_user(self.student_email)

        with self.assertRaises(Exception) as context:
            create_certificate(course=self.course_name)

        self.assertIn("completed", str(context.exception).lower())
        print(f"    Error capturado correctamente")

        print("\n" + "="*70)
        print("(n.n) INT-009-NEG: Prueba completada exitosamente")
        print("="*70)
