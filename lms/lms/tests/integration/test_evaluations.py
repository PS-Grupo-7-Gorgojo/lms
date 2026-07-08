"""
Pruebas de integración para Módulo 5: Evaluaciones
Casos: INT-007 (Quiz requiere nota aprobatoria)
"""

import frappe
import json
from frappe.tests import IntegrationTestCase
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz


class TestQuizValidation(IntegrationTestCase):
    """
    Prueba de integración para la validación de quizzes
    Verifica que un quiz con nota aprobatoria solo permita avanzar si se aprueba
    """

    def setUp(self):
        """Configuración antes de CADA prueba"""
        super().setUp()
        frappe.set_user("Administrator")

        # --- 1. Crear curso ---
        self.course_title = f"Curso Quiz {frappe.generate_hash(length=6)}"
        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": self.course_title,
            "published": 1,
            "short_introduction": "Curso de prueba para quiz",
            "description": "Este curso se utiliza para probar la validación de quizzes"
        })
        course.append("instructors", {"instructor": "Administrator"})
        course.insert()
        self.course_name = course.name
        print(f"✅ Curso '{self.course_title}' creado (ID: {self.course_name})")

        # --- 2. Crear capítulo con referencia ---
        chapter = frappe.get_doc({
            "doctype": "Course Chapter",
            "title": "Capítulo 1: Evaluación",
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
        print(f"✅ Capítulo '{self.chapter_name}' creado")

        # --- 3. Crear lección con referencia ---
        self.lesson_title = "Lección con Quiz"
        lesson = frappe.get_doc({
            "doctype": "Course Lesson",
            "title": self.lesson_title,
            "chapter": self.chapter_name,
            "course": self.course_name,
            "content": json.dumps({
                "blocks": [
                    {
                        "type": "quiz",
                        "data": {
                            "quiz": "test-quiz-validation"  # Se actualizará después
                        }
                    }
                ]
            })
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
        print(f"✅ Lección '{self.lesson_name}' creada")

        # --- 4. Crear quiz con passing_percentage = 70% ---
        self.quiz_name = f"test-quiz-validation-{frappe.generate_hash(length=6)}"
        quiz = frappe.get_doc({
            "doctype": "LMS Quiz",
            "title": "Quiz de Validación",
            "name": self.quiz_name,
            "passing_percentage": 70,
            "course": self.course_name,
            "lesson": self.lesson_name,
            "max_attempts": 0,  # Ilimitado
            "total_marks": 15
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
                "correct": 1,  # París es la correcta (opción 1)
                "marks": 5
            },
            {
                "question": "¿Cuánto es 2 + 2?",
                "type": "Multiple Choice",
                "option_1": "3",
                "option_2": "4",
                "option_3": "5",
                "correct": 2,  # 4 es la correcta (opción 2)
                "marks": 5
            },
            {
                "question": "¿Qué color es el cielo?",
                "type": "Multiple Choice",
                "option_1": "Rojo",
                "option_2": "Verde",
                "option_3": "Azul",
                "correct": 3,  # Azul es la correcta (opción 3)
                "marks": 5
            }
        ]

        for q in questions:
            quiz.append("questions", {
                "question": q["question"],
                "type": q["type"],
                "option_1": q["option_1"],
                "option_2": q["option_2"],
                "option_3": q["option_3"],
                "correct": q["correct"],
                "marks": q["marks"]
            })

        quiz.save()
        frappe.db.commit()

        # ✅ Actualizar la lección con el nombre real del quiz
        lesson.content = json.dumps({
            "blocks": [
                {
                    "type": "quiz",
                    "data": {
                        "quiz": self.quiz_name
                    }
                }
            ]
        })
        lesson.save()
        frappe.db.commit()
        print(f"✅ Quiz '{self.quiz_name}' creado con passing_percentage=70%")

        # --- 5. Crear usuario estudiante ---
        self.student_email = f"test_student_quiz_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.student_email,
            "first_name": "Test",
            "last_name": "Quiz Student",
            "send_welcome_email": 0
        })
        user.insert()
        user.add_roles("LMS Student")
        frappe.db.commit()
        print(f"✅ Usuario '{self.student_email}' creado con rol LMS Student")

    def tearDown(self):
        """Limpieza después de CADA prueba"""
        frappe.db.rollback()
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
        print("🧪 INT-007: Quiz requiere nota aprobatoria (70%)")
        print("="*70)

        # --- 1. Crear matrícula ---
        print("\n📖 Paso 1: Crear matrícula")
        enrollment = frappe.get_doc({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name
        })
        enrollment.flags.ignore_links = True
        enrollment.insert()
        frappe.db.commit()
        print(f"  ✅ Matrícula creada: {enrollment.name}")

        # --- 2. Verificar progreso inicial (sin lecciones completadas) ---
        print("\n📖 Paso 2: Verificar progreso inicial")
        progress_count = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count, 0, "Ya hay lecciones completadas")
        print("  ✅ No hay lecciones completadas (progreso 0%)")

        # --- 3. CASO A: Enviar quiz con nota BAJA (65% - no aprueba) ---
        print("\n📖 Paso 3: CASO A - Enviar quiz con nota BAJA (65%)")

        # Obtener el quiz
        quiz = frappe.get_doc("LMS Quiz", self.quiz_name)

        # Responder incorrectamente 1 pregunta (2 correctas de 3 = 66.6% ≈ 65%)
        # Para obtener exactamente 65%: 10/15 = 66.6% (2 correctas de 3)
        # Como no podemos obtener exactamente 65%, usamos 2 correctas (66.6%) que es < 70%
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

        # ✅ Cambiar al usuario estudiante
        frappe.set_user(self.student_email)

        # Enviar el quiz con nota baja
        submission_low = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results_low)
        )
        frappe.db.commit()

        print(f"  ✅ Quiz enviado (nota baja)")
        print(f"     Score: {submission_low['score']}/{submission_low['score_out_of']}")
        print(f"     Porcentaje: {submission_low['percentage']}%")
        print(f"     Aprueba: {submission_low['pass']}")

        self.assertFalse(submission_low['pass'],
            f"El quiz debería fallar con {submission_low['percentage']}% < 70%")
        print(f"  ✅ Porcentaje {submission_low['percentage']}% < 70% (NO aprueba)")

        # --- 4. Verificar que el progreso NO avanzó ---
        print("\n📖 Paso 4: Verificar que el progreso NO avanzó")
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
        print("  ✅ Progreso NO avanzó (nota no aprobatoria)")

        # --- 5. CASO B: Enviar quiz con nota ALTA (100% - aprueba) ---
        print("\n📖 Paso 5: CASO B - Enviar quiz con nota ALTA (100%)")

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

        # Enviar el quiz con nota alta
        submission_high = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results_high)
        )
        frappe.db.commit()

        print(f"  ✅ Quiz enviado (nota alta)")
        print(f"     Score: {submission_high['score']}/{submission_high['score_out_of']}")
        print(f"     Porcentaje: {submission_high['percentage']}%")
        print(f"     Aprueba: {submission_high['pass']}")

        self.assertTrue(submission_high['pass'],
            f"El quiz debería aprobar con {submission_high['percentage']}% >= 70%")
        print(f"  ✅ Porcentaje {submission_high['percentage']}% >= 70% (APRUEBA)")

        # --- 6. Verificar que el progreso SÍ avanzó ---
        print("\n📖 Paso 6: Verificar que el progreso SÍ avanzó")
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
        print("  ✅ Progreso avanzó (nota aprobatoria)")

        # --- 7. Verificar que la lección está completada ---
        print("\n📖 Paso 7: Verificar que la lección está completada")
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
        self.assertEqual(progress.lesson, self.lesson_name,
            "La lección completada no es la correcta")
        print(f"  ✅ Lección completada: {progress.lesson}")
        print(f"  ✅ Status: {progress.status}")

        # --- 8. Verificar el progreso del curso ---
        print("\n📖 Paso 8: Verificar progreso del curso")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100,
            f"El progreso del curso no es 100%, es {enrollment.progress}%")
        print(f"  ✅ Progreso del curso: {enrollment.progress}%")

        print("\n" + "="*70)
        print("✅ INT-007: Prueba completada exitosamente")
        print("   - Quiz con nota BAJA (< 70%) → NO avanza")
        print("   - Quiz con nota ALTA (>= 70%) → SI avanza")
        print("   - Lección completada correctamente")
        print("   - Progreso del curso 100%")
        print("="*70)
