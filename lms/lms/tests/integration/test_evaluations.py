"""
Pruebas de integración para Módulo 5: Evaluaciones
Casos: INT-007 (Quiz requiere nota aprobatoria)
"""

import frappe
from frappe.tests import IntegrationTestCase
from lms.lms.api import upsert_chapter, add_lesson, mark_lesson_progress


class TestQuizValidation(IntegrationTestCase):
    """
    Prueba de integración para la validación de quizzes
    Verifica que un quiz con nota aprobatoria solo permita avanzar si se aprueba
    """

    @classmethod
    def setUpClass(cls):
        """Configuración inicial: crear curso, capítulo, lección, quiz y usuario"""
        super().setUpClass()
        frappe.set_user("Administrator")

        # --- 1. Crear curso ---
        cls.course_name = "test-course-quiz-validation"
        if not frappe.db.exists("LMS Course", cls.course_name):
            course = frappe.get_doc({
                "doctype": "LMS Course",
                "title": "Curso para Validación de Quiz",
                "course_name": cls.course_name,
                "published": 1
            })
            course.insert()
            frappe.db.commit()
            print(f" Curso '{cls.course_name}' creado")

        # --- 2. Crear capítulo ---
        chapter = upsert_chapter(
            title="Capítulo 1: Evaluación",
            course=cls.course_name,
            is_scorm_package=False
        )
        cls.chapter_name = chapter.name
        print(f" Capítulo '{cls.chapter_name}' creado")

        # --- 3. Crear lección con quiz ---
        cls.lesson_title = "Lección con Quiz"
        lesson = add_lesson(
            title=cls.lesson_title,
            chapter=cls.chapter_name,
            course=cls.course_name,
            idx=1
        )
        cls.lesson_name = lesson.name
        print(f" Lección '{cls.lesson_name}' creada")

        # --- 4. Crear quiz con passing_percentage = 70% ---
        cls.quiz_name = "test-quiz-validation"
        if not frappe.db.exists("LMS Quiz", cls.quiz_name):
            quiz = frappe.get_doc({
                "doctype": "LMS Quiz",
                "title": "Quiz de Validación",
                "name": cls.quiz_name,
                "passing_percentage": 70,
                "course": cls.course_name,
                "lesson": cls.lesson_name
            })
            quiz.insert()

            # Agregar preguntas al quiz (3 preguntas de 5 puntos cada una = 15 puntos total)
            questions = [
                {
                    "question": "¿Cuál es la capital de Francia?",
                    "type": "Multiple Choice",
                    "option_1": "París",
                    "option_2": "Londres",
                    "option_3": "Berlín",
                    "correct": 1  # París es la correcta
                },
                {
                    "question": "¿Cuánto es 2 + 2?",
                    "type": "Multiple Choice",
                    "option_1": "3",
                    "option_2": "4",
                    "option_3": "5",
                    "correct": 2  # 4 es la correcta
                },
                {
                    "question": "¿Qué color es el cielo?",
                    "type": "Multiple Choice",
                    "option_1": "Rojo",
                    "option_2": "Verde",
                    "option_3": "Azul",
                    "correct": 3  # Azul es la correcta
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
            print(f"   Porcentaje de aprobación: 70%")

        # --- 5. Crear usuario estudiante ---
        cls.student_email = "test_student_quiz@example.com"
        if not frappe.db.exists("User", cls.student_email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": cls.student_email,
                "first_name": "Test",
                "last_name": "Quiz Student",
                "send_welcome_email": 0
            })
            user.insert()
            user.add_roles("LMS Student")
            frappe.db.commit()
            print(f" Usuario '{cls.student_email}' creado con rol LMS Student")

    @classmethod
    def tearDownClass(cls):
        """Limpieza final: eliminar curso, quiz y usuario"""

        # Eliminar quiz
        if frappe.db.exists("LMS Quiz", cls.quiz_name):
            frappe.delete_doc("LMS Quiz", cls.quiz_name, force=True)

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

        # Limpiar quiz submissions previos
        if frappe.db.exists("LMS Quiz Submission", {"member": self.student_email, "quiz": self.quiz_name}):
            submissions = frappe.get_all("LMS Quiz Submission", {
                "member": self.student_email,
                "quiz": self.quiz_name
            })
            for sub in submissions:
                frappe.delete_doc("LMS Quiz Submission", sub.name, force=True)

        frappe.db.commit()

    def tearDown(self):
        """Limpieza después de cada prueba"""
        super().tearDown()

    # ======================================================================
    # INT-007: Quiz requiere nota aprobatoria
    # ======================================================================

    def test_int_007_quiz_requires_passing_grade(self):
        """
        INT-007: Verificar que un quiz con passing_percentage=70%
        solo permita avanzar si se obtiene >= 70%
        """
        print("\n" + "="*70)
        print(">  INT-007: Quiz requiere nota aprobatoria (70%)")
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

        # --- 2. Verificar progreso inicial ---
        print("\n Paso 2: Verificar progreso inicial (sin completar lecciones)")
        progress_count = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count, 0, "Ya hay lecciones completadas")
        print("   No hay lecciones completadas (progreso 0%)")

        # --- 3. Intentar completar la lección sin aprobar el quiz ---
        print("\n Paso 3: Intentar completar lección sin aprobar quiz")
        mark_lesson_progress(self.course_name, 1, 1)

        # Verificar que NO se completó la lección
        progress_count_after = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count_after, 0,
            "La lección se completó a pesar de no haber aprobado el quiz")
        print("   La lección NO se completó (quiz no aprobado aún)")

        # --- 4. CASO A: Enviar quiz con nota BAJA (60% - no aprueba) ---
        print("\n Paso 4: CASO A - Enviar quiz con nota BAJA (60%)")
        from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

        # Obtener el quiz
        quiz = frappe.get_doc("LMS Quiz", self.quiz_name)

        # Responder incorrectamente 1 pregunta (2 correctas de 3 = 66%, pero como cada pregunta vale 5 puntos, 10/15 = 66.6%)
        # Para obtener 60%: 9/15 = 60% (responder 2 preguntas correctamente y 1 incorrecta)
        # Como cada pregunta vale 5 puntos: 2 correctas = 10 puntos, 1 incorrecta = 0, total 10/15 = 66.6%
        # Para obtener exactamente 60% necesitaríamos un quiz con 5 preguntas de 3 puntos cada una
        # Para simplificar, usaremos 66.6% que es < 70%

        results_low = [
            {
                "question_name": quiz.questions[0].question,
                "answer": [quiz.questions[0].option_1]  # Correcta
            },
            {
                "question_name": quiz.questions[1].question,
                "answer": [quiz.questions[1].option_2]  # Correcta
            },
            {
                "question_name": quiz.questions[2].question,
                "answer": [quiz.questions[2].option_2]  # Incorrecta (debería ser option_3)
            }
        ]

        submission_low = submit_quiz(
            quiz=self.quiz_name,
            results=results_low
        )
        frappe.db.commit()

        print(f"   Quiz enviado (nota baja)")
        print(f"     Score: {submission_low.score}/{submission_low.score_out_of}")
        print(f"     Porcentaje: {submission_low.percentage}%")
        self.assertLess(submission_low.percentage, 70,
            f"El porcentaje debería ser menor a 70%, es {submission_low.percentage}%")
        print(f"   Porcentaje {submission_low.percentage}% < 70% (NO aprueba)")

        # Verificar que el progreso sigue sin avanzar
        progress_count_low = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count_low, 0,
            "La lección se completó con nota baja (< 70%)")
        print("   Progreso NO avanzó (nota no aprobatoria)")

        # --- 5. CASO B: Enviar quiz con nota ALTA (100% - aprueba) ---
        print("\n Paso 5: CASO B - Enviar quiz con nota ALTA (100%)")

        # Responder correctamente TODAS las preguntas
        results_high = [
            {
                "question_name": quiz.questions[0].question,
                "answer": [quiz.questions[0].option_1]  # Correcta
            },
            {
                "question_name": quiz.questions[1].question,
                "answer": [quiz.questions[1].option_2]  # Correcta
            },
            {
                "question_name": quiz.questions[2].question,
                "answer": [quiz.questions[2].option_3]  # Correcta
            }
        ]

        submission_high = submit_quiz(
            quiz=self.quiz_name,
            results=results_high
        )
        frappe.db.commit()

        print(f"   Quiz enviado (nota alta)")
        print(f"     Score: {submission_high.score}/{submission_high.score_out_of}")
        print(f"     Porcentaje: {submission_high.percentage}%")
        self.assertGreaterEqual(submission_high.percentage, 70,
            f"El porcentaje debería ser >= 70%, es {submission_high.percentage}%")
        print(f"   Porcentaje {submission_high.percentage}% >= 70% (APRUEBA)")

        # --- 6. Marcar progreso de la lección (ahora debería permitir) ---
        print("\n Paso 6: Marcar progreso de la lección (con quiz aprobado)")
        mark_lesson_progress(self.course_name, 1, 1)

        # Verificar que la lección se completó
        progress_count_high = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count_high, 1,
            "La lección no se completó a pesar de haber aprobado el quiz")
        print("   Lección completada (quiz aprobado)")

        # --- 7. Verificar que la lección está marcada como completada ---
        print("\n Paso 7: Verificar que la lección está completada")
        progress = frappe.db.get_value(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            },
            ["name", "lesson", "status"],
            as_dict=True
        )

        self.assertIsNotNone(progress, "No se encontró el progreso de la lección")
        print(f"   Lección completada: {progress.lesson}")
        print(f"   Status: {progress.status}")

        # --- 8. Verificar el progreso del curso ---
        print("\n Paso 8: Verificar progreso del curso")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100,
            f"El progreso del curso no es 100%, es {enrollment.progress}%")
        print(f"   Progreso del curso: {enrollment.progress}%")

        print("\n" + "="*70)
        print(" INT-007: Prueba completada exitosamente")
        print("   - Quiz con nota BAJA (< 70%) → NO avanza")
        print("   - Quiz con nota ALTA (>= 70%) → SI avanza")
        print("   - Lección completada correctamente")
        print("   - Progreso del curso 100%")
        print("="*70)

    # ======================================================================
    # CASO NEGATIVO: Quiz sin respuestas
    # ======================================================================

    def test_quiz_without_answers(self):
        """
        INT-007-NEG: Intentar enviar quiz sin respuestas (debe fallar)
        """
        print("\n" + "="*70)
        print("🧪 INT-007-NEG: Enviar quiz sin respuestas")
        print("="*70)

        from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

        # Intentar enviar quiz con resultados vacíos
        with self.assertRaises(Exception) as context:
            submit_quiz(
                quiz=self.quiz_name,
                results=[]
            )

        print("   Error capturado correctamente (resultados vacíos)")
        print("="*70)

    def test_quiz_incorrect_format(self):
        """
        INT-007-NEG: Intentar enviar quiz con formato incorrecto
        """
        print("\n" + "="*70)
        print("🧪 INT-007-NEG: Enviar quiz con formato incorrecto")
        print("="*70)

        from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

        # Intentar enviar quiz con formato incorrecto (no es una lista)
        with self.assertRaises(Exception) as context:
            submit_quiz(
                quiz=self.quiz_name,
                results="invalid-format"
            )

        print("   Error capturado correctamente (formato inválido)")
        print("="*70)
