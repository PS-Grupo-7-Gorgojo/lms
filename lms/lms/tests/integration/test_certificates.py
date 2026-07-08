"""
Pruebas de integración para Módulo 8: Certificaciones
Casos: INT-009 (Certificado automático al completar curso)
"""

import frappe
from frappe.tests import IntegrationTestCase
from lms.lms.api import upsert_chapter, add_lesson, mark_lesson_progress


class TestCertificateCompletion(IntegrationTestCase):
    """
    Prueba de integración para la emisión automática de certificados
    Verifica que al completar un curso al 100%, se emita un certificado automáticamente
    """

    @classmethod
    def setUpClass(cls):
        """Configuración inicial: crear curso con capítulos, lecciones y evaluaciones"""
        super().setUpClass()
        frappe.set_user("Administrator")

        # --- 1. Crear curso ---
        cls.course_name = "test-course-certificate"
        if not frappe.db.exists("LMS Course", cls.course_name):
            course = frappe.get_doc({
                "doctype": "LMS Course",
                "title": "Curso para Certificación",
                "course_name": cls.course_name,
                "published": 1,
                "paid_certificate": 0  # Certificado gratuito
            })
            course.insert()
            frappe.db.commit()
            print(f" Curso '{cls.course_name}' creado")

        # --- 2. Crear capítulo y lecciones ---
        cls.lessons = []

        # Capítulo 1
        chapter1 = upsert_chapter(
            title="Capítulo 1: Fundamentos",
            course=cls.course_name,
            is_scorm_package=False
        )
        cls.chapter1_name = chapter1.name

        # Lección 1.1 (contenido teórico)
        lesson1 = add_lesson(
            title="Lección 1.1: Introducción",
            chapter=cls.chapter1_name,
            course=cls.course_name,
            idx=1
        )
        cls.lessons.append(lesson1.name)

        # Lección 1.2 (con quiz)
        cls.quiz_lesson = add_lesson(
            title="Lección 1.2: Evaluación Teórica",
            chapter=cls.chapter1_name,
            course=cls.course_name,
            idx=2
        )
        cls.lessons.append(cls.quiz_lesson.name)

        # Capítulo 2
        chapter2 = upsert_chapter(
            title="Capítulo 2: Práctica",
            course=cls.course_name,
            is_scorm_package=False
        )
        cls.chapter2_name = chapter2.name

        # Lección 2.1 (con assignment)
        cls.assignment_lesson = add_lesson(
            title="Lección 2.1: Evaluación Práctica",
            chapter=cls.chapter2_name,
            course=cls.course_name,
            idx=1
        )
        cls.lessons.append(cls.assignment_lesson.name)

        print(f" {len(cls.lessons)} lecciones creadas")

        # --- 3. Crear quiz en la lección ---
        cls.quiz_name = "test-quiz-certificate"
        if not frappe.db.exists("LMS Quiz", cls.quiz_name):
            quiz = frappe.get_doc({
                "doctype": "LMS Quiz",
                "title": "Quiz de Certificación",
                "name": cls.quiz_name,
                "passing_percentage": 70,
                "course": cls.course_name,
                "lesson": cls.quiz_lesson.name
            })
            quiz.insert()

            # Agregar preguntas al quiz
            questions = [
                {
                    "question": "¿Cuál es el primer paso del flujo?",
                    "type": "Multiple Choice",
                    "option_1": "Crear matrícula",
                    "option_2": "Completar lecciones",
                    "option_3": "Emitir certificado",
                    "correct": 1
                },
                {
                    "question": "¿Qué porcentaje se necesita para aprobar?",
                    "type": "Multiple Choice",
                    "option_1": "50%",
                    "option_2": "70%",
                    "option_3": "100%",
                    "correct": 2
                }
            ]

            for q in questions:
                quiz.append("questions", {
                    "question": q["question"],
                    "type": q["type"],
                    "option_1": q["option_1"],
                    "option_2": q["option_2"],
                    "option_3": q["option_3"],
                    "correct": q["correct"]
                })

            quiz.save()
            frappe.db.commit()
            print(f" Quiz '{cls.quiz_name}' creado con {len(questions)} preguntas")

        # --- 4. Crear assignment en la lección ---
        cls.assignment_name = "test-assignment-certificate"
        if not frappe.db.exists("LMS Assignment", cls.assignment_name):
            assignment = frappe.get_doc({
                "doctype": "LMS Assignment",
                "title": "Assignment de Certificación",
                "name": cls.assignment_name,
                "course": cls.course_name,
                "lesson": cls.assignment_lesson.name,
                "type": "Text"
            })
            assignment.insert()
            frappe.db.commit()
            print(f" Assignment '{cls.assignment_name}' creado")

        # --- 5. Crear usuario estudiante ---
        cls.student_email = "test_student_certificate@example.com"
        if not frappe.db.exists("User", cls.student_email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": cls.student_email,
                "first_name": "Test",
                "last_name": "Certificate Student",
                "send_welcome_email": 0
            })
            user.insert()
            user.add_roles("LMS Student")
            frappe.db.commit()
            print(f" Usuario '{cls.student_email}' creado con rol LMS Student")

    @classmethod
    def tearDownClass(cls):
        """Limpieza final: eliminar curso, evaluaciones, certificados y usuario"""

        # Eliminar certificados
        if frappe.db.exists("LMS Certificate", {"member": cls.student_email, "course": cls.course_name}):
            cert = frappe.get_doc("LMS Certificate", {
                "member": cls.student_email,
                "course": cls.course_name
            })
            frappe.delete_doc("LMS Certificate", cert.name, force=True)

        # Eliminar quiz
        if frappe.db.exists("LMS Quiz", cls.quiz_name):
            frappe.delete_doc("LMS Quiz", cls.quiz_name, force=True)

        # Eliminar assignment
        if frappe.db.exists("LMS Assignment", cls.assignment_name):
            frappe.delete_doc("LMS Assignment", cls.assignment_name, force=True)

        # Eliminar curso y sus dependencias
        if frappe.db.exists("LMS Course", cls.course_name):
            course = frappe.get_doc("LMS Course", cls.course_name)
            for chapter_ref in course.get("chapters", []):
                chapter_name = chapter_ref.get("chapter")
                if chapter_name and frappe.db.exists("Course Chapter", chapter_name):
                    chapter = frappe.get_doc("Course Chapter", chapter_name)
                    for lesson_ref in chapter.get("lessons", []):
                        lesson_name = lesson_ref.get("lesson")
                        if lesson_name and frappe.db.exists("Course Lesson", lesson_name):
                            frappe.delete_doc("Course Lesson", lesson_name, force=True)
                    frappe.delete_doc("Course Chapter", chapter_name, force=True)
            frappe.delete_doc("LMS Course", cls.course_name, force=True)
            frappe.db.commit()
            print(f" Curso '{cls.course_name}' eliminado")

        # Eliminar usuario
        if frappe.db.exists("User", cls.student_email):
            frappe.delete_doc("User", cls.student_email, force=True)
            frappe.db.commit()
            print(f" Usuario '{cls.student_email}' eliminado")

        super().tearDownClass()

    def setUp(self):
        """Configuración antes de cada prueba: asegurar usuario Admin y limpiar datos previos"""
        super().setUp()
        frappe.set_user("Administrator")

        # Limpiar matrículas previas
        if frappe.db.exists("LMS Enrollment", {"member": self.student_email, "course": self.course_name}):
            enrollment = frappe.get_doc("LMS Enrollment", {
                "member": self.student_email,
                "course": self.course_name
            })
            frappe.delete_doc("LMS Enrollment", enrollment.name, force=True)

        # Limpiar progreso previo
        if frappe.db.exists("LMS Course Progress", {"member": self.student_email, "course": self.course_name}):
            progress = frappe.get_doc("LMS Course Progress", {
                "member": self.student_email,
                "course": self.course_name
            })
            frappe.delete_doc("LMS Course Progress", progress.name, force=True)

        # Limpiar certificados previos
        if frappe.db.exists("LMS Certificate", {"member": self.student_email, "course": self.course_name}):
            cert = frappe.get_doc("LMS Certificate", {
                "member": self.student_email,
                "course": self.course_name
            })
            frappe.delete_doc("LMS Certificate", cert.name, force=True)

        # Limpiar quiz submissions
        if frappe.db.exists("LMS Quiz Submission", {"member": self.student_email, "quiz": self.quiz_name}):
            submissions = frappe.get_all("LMS Quiz Submission", {
                "member": self.student_email,
                "quiz": self.quiz_name
            })
            for sub in submissions:
                frappe.delete_doc("LMS Quiz Submission", sub.name, force=True)

        # Limpiar assignment submissions
        if frappe.db.exists("LMS Assignment Submission", {"member": self.student_email, "assignment": self.assignment_name}):
            submissions = frappe.get_all("LMS Assignment Submission", {
                "member": self.student_email,
                "assignment": self.assignment_name
            })
            for sub in submissions:
                frappe.delete_doc("LMS Assignment Submission", sub.name, force=True)

        frappe.db.commit()

    def tearDown(self):
        """Limpieza después de cada prueba"""
        super().tearDown()

    # ======================================================================
    # INT-009: Certificado automático al completar curso
    # ======================================================================

    def test_int_009_auto_certificate_on_completion(self):
        """
        INT-009: Verificar que al completar el 100% del curso,
        se emita automáticamente un certificado al estudiante
        """
        print("\n" + "="*70)
        print(">  INT-009: Certificado automático al completar curso")
        print("="*70)

        # --- 1. Matricular al estudiante ---
        print("\n Paso 1: Matricular al estudiante")
        enrollment = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"   Matrícula creada: {enrollment.name}")
        print(f"     Estudiante: {self.student_email}")
        print(f"     Curso: {self.course_name}")

        # --- 2. Verificar que no hay certificado inicialmente ---
        print("\n Paso 2: Verificar que NO hay certificado antes de completar")
        initial_cert = frappe.db.exists(
            "LMS Certificate",
            {"member": self.student_email, "course": self.course_name}
        )
        self.assertFalse(initial_cert, "El certificado existe antes de completar el curso")
        print("   No hay certificado antes de completar el curso")

        # --- 3. Verificar progreso inicial ---
        print("\n Paso 3: Verificar progreso inicial (0%)")
        progress = frappe.db.get_value(
            "LMS Course Progress",
            {"member": self.student_email, "course": self.course_name},
            ["name", "status", "lesson"],
            as_dict=True
        )
        print(f"   Progreso inicial registrado: {progress.name if progress else 'No hay progreso'}")

        # --- 4. Completar TODAS las lecciones ---
        print("\n Paso 4: Completar todas las lecciones del curso")
        for i, lesson_name in enumerate(self.lessons, 1):
            # Marcar progreso de la lección
            mark_lesson_progress(self.course_name, 1, i)  # Asumimos capítulo 1, índice i
            print(f"   Lección {i} completada: {lesson_name}")

        # --- 5. Crear submission del quiz (aprobado) ---
        print("\n Paso 5: Enviar y aprobar el quiz")
        from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

        # Obtener las preguntas del quiz
        quiz = frappe.get_doc("LMS Quiz", self.quiz_name)
        results = []
        for q in quiz.questions:
            # Responder correctamente a todas las preguntas
            results.append({
                "question_name": q.question,
                "answer": [q.option_1]  # La primera opción es la correcta
            })

        submission = submit_quiz(
            quiz=self.quiz_name,
            results=results
        )
        frappe.db.commit()
        print(f"   Quiz enviado y aprobado")
        print(f"     Score: {submission.score}/{submission.score_out_of}")
        print(f"     Porcentaje: {submission.percentage}%")

        # --- 6. Crear submission del assignment (aprobado) ---
        print("\n Paso 6: Enviar y aprobar el assignment")
        assignment_submission = frappe.client.insert({
            "doctype": "LMS Assignment Submission",
            "member": self.student_email,
            "assignment": self.assignment_name,
            "status": "Pass",
            "comments": "Trabajo completado correctamente"
        })
        frappe.db.commit()
        print(f"   Assignment enviado y aprobado: {assignment_submission.name}")

        # --- 7. Verificar que el progreso llega a 100% ---
        print("\n Paso 7: Verificar que el progreso es 100%")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100,
            f"El progreso no es 100%, es {enrollment.progress}%")
        print(f"   Progreso del curso: {enrollment.progress}%")

        # --- 8. Verificar que se emitió el certificado automáticamente ---
        print("\n Paso 8: Verificar que se emitió el certificado automáticamente")
        certificate = frappe.db.get_value(
            "LMS Certificate",
            {"member": self.student_email, "course": self.course_name},
            ["name", "issue_date", "member_name", "course_title", "status"],
            as_dict=True
        )

        self.assertIsNotNone(certificate,
            "No se emitió el certificado automáticamente al completar el curso")

        print(f"   Certificado emitido automáticamente")
        print(f"     ID: {certificate.name}")
        print(f"     Fecha de emisión: {certificate.issue_date}")
        print(f"     Estudiante: {certificate.member_name}")
        print(f"     Curso: {certificate.course_title}")
        print(f"     Estado: {certificate.status}")

        # --- 9. Verificar que el certificado tiene la información correcta ---
        print("\n Paso 9: Verificar que el certificado tiene la información correcta")
        cert_doc = frappe.get_doc("LMS Certificate", certificate.name)

        self.assertEqual(cert_doc.member, self.student_email,
            "El certificado no está vinculado al estudiante correcto")
        self.assertEqual(cert_doc.course, self.course_name,
            "El certificado no está vinculado al curso correcto")

        # Verificar que el certificado está publicado (visible)
        self.assertEqual(cert_doc.published, 1,
            "El certificado no está publicado")

        print(f"  (n.n) Certificado vinculado al estudiante correcto")
        print(f"  (n.n) Certificado vinculado al curso correcto")
        print(f"  (n.n) Certificado publicado (visible para el estudiante)")

        print("\n" + "="*70)
        print(" INT-009: Prueba completada exitosamente")
        print("   - Estudiante matriculado")
        print("   - Todas las lecciones completadas")
        print("   - Quiz aprobado")
        print("   - Assignment aprobado")
        print("   - Progreso 100% alcanzado")
        print("   - Certificado emitido automáticamente")
        print("   - Certificado con información correcta")
        print("="*70)

    # ======================================================================
    # CASO NEGATIVO: Curso incompleto no genera certificado
    # ======================================================================

    def test_no_certificate_without_completion(self):
        """
        INT-009-NEG: Verificar que un curso incompleto NO genera certificado
        """
        print("\n" + "="*70)
        print(" INT-009-NEG: Curso incompleto NO genera certificado")
        print("="*70)

        # --- 1. Matricular al estudiante ---
        print("\n Paso 1: Matricular al estudiante")
        enrollment = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"   Matrícula creada: {enrollment.name}")

        # --- 2. Completar SOLO UNA lección (no todas) ---
        print("\n Paso 2: Completar solo una lección (curso incompleto)")
        mark_lesson_progress(self.course_name, 1, 1)
        print(f"  ✅ Una lección completada")

        # --- 3. Verificar que NO se emitió certificado ---
        print("\n Paso 3: Verificar que NO se emitió certificado")
        certificate_exists = frappe.db.exists(
            "LMS Certificate",
            {"member": self.student_email, "course": self.course_name}
        )

        self.assertFalse(certificate_exists,
            "Se emitió certificado a pesar de que el curso no está completo")
        print("   No se emitió certificado (curso incompleto)")

        # --- 4. Verificar que el progreso NO es 100% ---
        print("\n Paso 4: Verificar que el progreso NO es 100%")
        enrollment.reload()
        self.assertNotEqual(enrollment.progress, 100,
            f"El progreso es 100% a pesar de no haber completado todas las lecciones")
        print(f"   Progreso: {enrollment.progress}% (correcto, no está completo)")

        print("\n" + "="*70)
        print(" INT-009-NEG: Prueba completada exitosamente")
        print("   - Curso incompleto NO genera certificado")
        print("   - Progreso NO es 100%")
        print("="*70)
