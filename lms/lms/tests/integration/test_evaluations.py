"""
Pruebas de integración para Módulo 5: Evaluaciones
Casos: INT-007 (Quiz requiere nota aprobatoria)
"""
import os
import unittest

import frappe
import json
from frappe.tests import IntegrationTestCase
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
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
        print(f"Curso '{self.course_title}' creado (ID: {self.course_name})")

        # --- 2. Crear capítulo ---
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
        print(f"Capítulo '{self.chapter_name}' creado")

        # --- 3. Crear preguntas ---
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

        # --- 4. Crear quiz (SIN especificar nombre, dejar que Frappe lo genere) ---
        quiz = frappe.get_doc({
            "doctype": "LMS Quiz",
            "title": "Quiz de Validación",
            "passing_percentage": 70,
            "course": self.course_name,
            "max_attempts": 0,
            "total_marks": 15
        })
        quiz.insert()

        # Guardar el nombre REAL generado por Frappe
        self.quiz_name = quiz.name
        print(f"Quiz creado con nombre REAL: {self.quiz_name} (título: Quiz de Validación)")

        # Agregar preguntas al quiz
        for q_name in self.question_names:
            quiz.append("questions", {
                "question": q_name,
                "marks": 5
            })

        quiz.save()
        frappe.db.commit()
        print(f"Preguntas agregadas al quiz")

        # --- 5. Crear lección con el nombre REAL del quiz ---
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
                            "quiz": self.quiz_name
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
        frappe.db.commit()
        print(f"Lección '{self.lesson_name}' creada con quiz embebido")

        # --- 6. Crear usuario estudiante ---
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
        print(f"Usuario '{self.student_email}' creado con rol LMS Student")

    def tearDown(self):
        """Limpieza después de CADA prueba"""
        frappe.db.rollback()
        super().tearDown()

    def test_int_007_quiz_requires_passing_grade(self):
        """
        INT-007: Verificar que un quiz con passing_percentage=70%
        solo permita avanzar si se obtiene >= 70%
        """
        print("\n" + "="*70)
        print(">  INT-007: Quiz requiere nota aprobatoria (70%)")
        print("="*70)

        # --- 1. Crear matrícula ---
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

        # --- 2. Verificar progreso inicial ---
        print("\nPaso 2: Verificar progreso inicial")
        progress_count = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count, 0, "Ya hay lecciones completadas")
        print("    No hay lecciones completadas (progreso 0%)")

        # --- 3. CASO A: Quiz con nota BAJA ---
        print("\nPaso 3: CASO A - Quiz con nota BAJA (66.6%)")

        results_low = [
            {
                "question_name": self.question_names[0],
                "answer": ["París"]  # Correcta
            },
            {
                "question_name": self.question_names[1],
                "answer": ["4"]  # Correcta
            },
            {
                "question_name": self.question_names[2],
                "answer": ["Verde"]  # Incorrecta
            }
        ]

        frappe.set_user(self.student_email)

        submission_low = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results_low)
        )
        frappe.db.commit()

        print(f"Quiz enviado (nota baja)")
        print(f"     Score: {submission_low['score']}/{submission_low['score_out_of']}")
        print(f"     Porcentaje: {submission_low['percentage']}%")
        print(f"     Aprueba: {submission_low['pass']}")

        self.assertFalse(submission_low['pass'])
        print(f"{submission_low['percentage']}% < 70% (NO aprueba)")

        # --- 4. Verificar que el progreso NO avanzó ---
        print("\nPaso 4: Verificar progreso NO avanzó")
        progress_count_low = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count_low, 0)
        print("    Progreso NO avanzó")

        # --- 5. CASO B: Quiz con nota ALTA ---
        print("\nPaso 5: CASO B - Quiz con nota ALTA (100%)")

        results_high = [
            {
                "question_name": self.question_names[0],
                "answer": ["París"]  # Correcta
            },
            {
                "question_name": self.question_names[1],
                "answer": ["4"]  # Correcta
            },
            {
                "question_name": self.question_names[2],
                "answer": ["Azul"]  # Correcta
            }
        ]

        submission_high = submit_quiz(
            quiz=self.quiz_name,
            results=json.dumps(results_high)
        )
        frappe.db.commit()

        print(f"Quiz enviado (nota alta)")
        print(f"     Score: {submission_high['score']}/{submission_high['score_out_of']}")
        print(f"     Porcentaje: {submission_high['percentage']}%")
        print(f"     Aprueba: {submission_high['pass']}")

        self.assertTrue(submission_high['pass'])
        print(f"{submission_high['percentage']}% >= 70% (APRUEBA)")

        # --- 6. Verificar que el progreso SÍ avanzó ---
        print("\nPaso 6: Verificar progreso SÍ avanzó")
        progress_count_high = frappe.db.count(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name,
                "status": "Complete"
            }
        )
        self.assertEqual(progress_count_high, 1)
        print("    Progreso avanzó")

        # --- 7. Verificar lección completada ---
        print("\nPaso 7: Verificar lección completada")
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

        self.assertIsNotNone(progress)
        print(f"    Lección completada: {progress.lesson}")

        # --- 8. Verificar progreso del curso ---
        print("\nPaso 8: Verificar progreso del curso")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100)
        print(f"    Progreso del curso: {enrollment.progress}%")

        print("\n" + "="*70)
        print("(n.n) INT-007: Prueba completada exitosamente")
        print("="*70)

	# ======================================================================
	# INT-008: Programming Exercise - Autoevaluación con test cases
	# ======================================================================

    def test_int_008_programming_exercise_evaluation(self):
	    """
	    INT-008: Verificar que un ejercicio de programación se autoevalúa
	    correctamente con casos de prueba y devuelve status 'Pass'
	    """
	    print("\n" + "="*70)
	    print(">  INT-008: Programming Exercise - Autoevaluación")
	    print("="*70)

	    # --- 1. Crear Programming Exercise con test cases ---
	    print("\nPaso 1: Crear ejercicio de programación")

	    # NO especificar 'name', dejar que Frappe lo genere
	    exercise = frappe.get_doc({
	        "doctype": "LMS Programming Exercise",
	        "title": f"Ejercicio de Suma {frappe.generate_hash(length=6)}",
	        "problem_statement": "Escribe una función 'suma(a, b)' que devuelva la suma de dos números.",
	        "test_cases": [
	            {
	                "input": "suma(2, 3)",
	                "expected_output": "5"
	            },
	            {
	                "input": "suma(-1, 1)",
	                "expected_output": "0"
	            },
	            {
	                "input": "suma(0, 0)",
	                "expected_output": "0"
	            }
	        ]
	    })
	    exercise.insert(ignore_permissions=True)
	    frappe.db.commit()
	    # Usar el nombre REAL generado por Frappe
	    exercise_name = exercise.name
	    print(f"     Ejercicio creado: {exercise_name}")
	    print(f"       Test cases: {len(exercise.test_cases)}")

	    # --- 2. Crear usuario estudiante ---
	    print("\nPaso 2: Crear usuario estudiante")
	    student_email = f"test_student_exercise_{frappe.generate_hash(length=6)}@example.com"
	    user = frappe.get_doc({
	        "doctype": "User",
	        "email": student_email,
	        "first_name": "Test",
	        "last_name": "Exercise Student",
	        "send_welcome_email": 0
	    })
	    user.insert()
	    user.add_roles("LMS Student")
	    frappe.db.commit()
	    print(f"     Usuario '{student_email}' creado con rol LMS Student")

	    # --- 3. Crear submission con código correcto (como Administrator) ---
	    print("\nPaso 3: Enviar código correcto (como Administrator)")

	    correct_code = """
def suma(a, b):
    return a + b
"""

	    from lms.lms.api import create_programming_exercise_submission

	    frappe.set_user("Administrator")

	    #  Verificar que el ejercicio existe con el nombre REAL
	    self.assertTrue(frappe.db.exists("LMS Programming Exercise", exercise_name),
	        f"El ejercicio '{exercise_name}' no existe en la base de datos")

	    submission_name = create_programming_exercise_submission(
	        exercise=exercise_name,
	        submission="new",
	        code=correct_code,
	        test_cases=[
	            {"input": "suma(2, 3)", "output": "5", "expected_output": "5", "status": "Passed"},
	            {"input": "suma(-1, 1)", "output": "0", "expected_output": "0", "status": "Passed"},
	            {"input": "suma(0, 0)", "output": "0", "expected_output": "0", "status": "Passed"}
	        ]
	    )
	    frappe.db.commit()
	    print(f"      Submission creada: {submission_name}")

	    # --- 4. Verificar status de la submission ---
	    print("\nPaso 4: Verificar status de la submission")
	    submission_doc = frappe.get_doc("LMS Programming Exercise Submission", submission_name)
	    self.assertEqual(submission_doc.status, "Passed",
	        f"El status debería ser 'Passed', es '{submission_doc.status}'")
	    print(f"      Status: {submission_doc.status}")

	    # --- 5. Verificar que todos los test cases pasaron ---
	    print("\nPaso 5: Verificar test cases")
	    for test_case in submission_doc.test_cases:
	        self.assertEqual(test_case.status, "Passed",
	            f"El test case '{test_case.input}' no pasó: {test_case.status}")
	        print(f"      Test case '{test_case.input}' → {test_case.status}")

	    # --- 6. Enviar código incorrecto (debe fallar) ---
	    print("\nPaso 6: Enviar código incorrecto (debe fallar)")

	    incorrect_code = """
def suma(a, b):
    return a - b  # Incorrecto: resta en lugar de suma
"""

	    submission_fail_name = create_programming_exercise_submission(
	        exercise=exercise_name,
	        submission="new",
	        code=incorrect_code,
	        test_cases=[
	            {"input": "suma(2, 3)", "output": "-1", "expected_output": "5", "status": "Failed"},
	            {"input": "suma(-1, 1)", "output": "-2", "expected_output": "0", "status": "Failed"},
	            {"input": "suma(0, 0)", "output": "0", "expected_output": "0", "status": "Passed"}
	        ]
	    )
	    frappe.db.commit()
	    print(f"     Submission incorrecta creada: {submission_fail_name}")

	    # --- 7. Verificar status incorrecto ---
	    print("\nPaso 7: Verificar status de la submission incorrecta")
	    submission_fail_doc = frappe.get_doc("LMS Programming Exercise Submission", submission_fail_name)
	    self.assertEqual(submission_fail_doc.status, "Failed",
	        f"El status debería ser 'Failed', es '{submission_fail_doc.status}'")
	    print(f"     Status: {submission_fail_doc.status} (esperado: Failed)")

	    # --- 8. Verificar que el estudiante NO puede crear submissions ---
	    print("\nPaso 8: Verificar que el estudiante NO puede crear submissions")
	    frappe.set_user(student_email)

	    with self.assertRaises(frappe.PermissionError) as context:
	        create_programming_exercise_submission(
	            exercise=exercise_name,
	            submission="new",
	            code=correct_code,
	            test_cases=[]
	        )

	    print("     Estudiante no puede crear submissions (Permiso denegado)")

	    # --- 9. Limpiar ---
	    print("\nPaso 9: Limpiar datos de prueba")
	    frappe.set_user("Administrator")

	    # Eliminar submissions
	    for sub_name in [submission_name, submission_fail_name]:
	        if frappe.db.exists("LMS Programming Exercise Submission", sub_name):
	            frappe.delete_doc("LMS Programming Exercise Submission", sub_name, force=True, ignore_permissions=True)

	    # Eliminar ejercicio
	    if frappe.db.exists("LMS Programming Exercise", exercise_name):
	        frappe.delete_doc("LMS Programming Exercise", exercise_name, force=True, ignore_permissions=True)

	    # Eliminar usuario
	    if frappe.db.exists("User", student_email):
	        frappe.delete_doc("User", student_email, force=True, ignore_permissions=True)

	    frappe.db.commit()
	    print("      Datos de prueba eliminados")

	    print("\n" + "="*70)
	    print("(n.n) INT-008: Prueba completada exitosamente")
	    print("   - Ejercicio de programación creado")
	    print("   - Código correcto → status Passed")
	    print("   - Código incorrecto → status Failed")
	    print("   - Estudiante no puede crear submissions (permiso verificado)")
	    print("="*70)
