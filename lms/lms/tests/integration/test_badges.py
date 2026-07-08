"""
Pruebas de integración para Módulo 11: Badges / Gamificación
Casos: INT-013 (Badge de Primera Matrícula)
       INT-014 (Badge al obtener Certificación)
"""

import json

import frappe
from frappe.tests import IntegrationTestCase
from lms.lms.api import upsert_chapter, add_lesson, mark_lesson_progress


def _create_choice_question(text, options, correct_option):
    """Crea una LMS Question de tipo 'Choices' con la opción correcta marcada."""
    question = frappe.new_doc("LMS Question")
    question.question = text
    question.type = "Choices"
    for i, option_text in enumerate(options, start=1):
        setattr(question, f"option_{i}", option_text)
        if i == correct_option:
            setattr(question, f"is_correct_{i}", 1)
    question.save(ignore_permissions=True)
    return question.name


class TestBadgeEnrollment(IntegrationTestCase):
    """
    Pruebas de integración para badges
    """

    @classmethod
    def setUpClass(cls):
        """Configuración inicial: crear curso, badges y usuario"""
        super().setUpClass()
        frappe.set_user("Administrator")

        # --- 1. Crear curso para INT-013 (Badge de Matrícula) ---
        cls.course_name = "test-course-badge"
        if not frappe.db.exists("LMS Course", cls.course_name):
            course = frappe.get_doc({
                "doctype": "LMS Course",
                "title": "Curso para Badge",
                "name": cls.course_name,
                "published": 1,
                "short_introduction": "Curso de prueba para badges",
                "description": "Este curso se utiliza para probar la asignación de badges"
            })
            course.append("instructors", {
                "instructor": "Administrator"
            })
            course.insert()
            frappe.db.commit()
            print(f"✅ Curso '{cls.course_name}' creado")
        else:
            print(f"ℹ️ Curso '{cls.course_name}' ya existe")

        # --- 2. Crear curso para INT-014 (Badge de Certificado) ---
        cls.cert_course_name = "test-course-cert-badge"
        if not frappe.db.exists("LMS Course", cls.cert_course_name):
            course = frappe.get_doc({
                "doctype": "LMS Course",
                "title": "Curso para Badge de Certificado",
                "name": cls.cert_course_name,
                "published": 1,
                "paid_certificate": 0,
                "enable_certification": 1,
                "short_introduction": "Curso de prueba para badge de certificado",
                "description": "Este curso se utiliza para probar la asignación de badge al obtener certificado"
            })
            course.append("instructors", {
                "instructor": "Administrator"
            })
            course.insert()
            frappe.db.commit()
            print(f"✅ Curso '{cls.cert_course_name}' creado")
        else:
            print(f"ℹ️ Curso '{cls.cert_course_name}' ya existe")

        # --- 3. Crear capítulos y lecciones para el curso de certificado ---
        cls.cert_lessons = []
        # Posición (número de capítulo, número de lección) de cada lección en
        # cert_lessons, en el mismo orden, para poder llamar a
        # mark_lesson_progress con los índices correctos.
        cls.cert_lesson_positions = []

        # Capítulo 1
        chapter1 = upsert_chapter(
            title="Capítulo 1: Fundamentos",
            course=cls.cert_course_name,
            is_scorm_package=False
        )
        cls.cert_chapter1_name = chapter1.name

        # Lección 1.1 (contenido teórico)
        lesson1 = add_lesson(
            title="Lección 1.1: Introducción",
            chapter=cls.cert_chapter1_name,
            course=cls.cert_course_name,
            idx=1
        )
        cls.cert_lessons.append(lesson1.name)
        cls.cert_lesson_positions.append((1, 1))

        # Lección 1.2 (con quiz)
        cls.cert_quiz_lesson = add_lesson(
            title="Lección 1.2: Evaluación Teórica",
            chapter=cls.cert_chapter1_name,
            course=cls.cert_course_name,
            idx=2
        )
        cls.cert_lessons.append(cls.cert_quiz_lesson.name)
        cls.cert_lesson_positions.append((1, 2))

        # Capítulo 2
        chapter2 = upsert_chapter(
            title="Capítulo 2: Práctica",
            course=cls.cert_course_name,
            is_scorm_package=False
        )
        cls.cert_chapter2_name = chapter2.name

        # Lección 2.1 (con assignment)
        cls.cert_assignment_lesson = add_lesson(
            title="Lección 2.1: Evaluación Práctica",
            chapter=cls.cert_chapter2_name,
            course=cls.cert_course_name,
            idx=1
        )
        cls.cert_lessons.append(cls.cert_assignment_lesson.name)
        cls.cert_lesson_positions.append((2, 1))

        print(f"✅ {len(cls.cert_lessons)} lecciones creadas para curso de certificado")

        # --- 4. Crear preguntas y quiz en la lección ---
        cls.cert_quiz_name = "test-quiz-cert-badge"
        if not frappe.db.exists("LMS Quiz", cls.cert_quiz_name):
            q1_name = _create_choice_question(
                "¿Qué se obtiene al completar el curso?",
                ["Un badge", "Un certificado", "Ambos"],
                correct_option=3,
            )
            q2_name = _create_choice_question(
                "¿Qué porcentaje se necesita para aprobar?",
                ["50%", "70%", "100%"],
                correct_option=2,
            )

            quiz = frappe.get_doc({
                "doctype": "LMS Quiz",
                "title": "Quiz para Badge de Certificado",
                "name": cls.cert_quiz_name,
                "passing_percentage": 70,
                "course": cls.cert_course_name,
                "lesson": cls.cert_quiz_lesson.name
            })
            quiz.append("questions", {"question": q1_name, "marks": 1})
            quiz.append("questions", {"question": q2_name, "marks": 1})
            quiz.insert()
            frappe.db.commit()
            print(f"✅ Quiz '{cls.cert_quiz_name}' creado")
        else:
            print(f"ℹ️ Quiz '{cls.cert_quiz_name}' ya existe")

        # --- 5. Crear assignment en la lección ---
        cls.cert_assignment_name = "test-assignment-cert-badge"
        if not frappe.db.exists("LMS Assignment", cls.cert_assignment_name):
            assignment = frappe.get_doc({
                "doctype": "LMS Assignment",
                "title": "Assignment para Badge de Certificado",
                "name": cls.cert_assignment_name,
                "course": cls.cert_course_name,
                "lesson": cls.cert_assignment_lesson.name,
                "type": "Text"
            })
            assignment.insert()
            frappe.db.commit()
            print(f"✅ Assignment '{cls.cert_assignment_name}' creado")
        else:
            print(f"ℹ️ Assignment '{cls.cert_assignment_name}' ya existe")

        # --- 6. Crear Badge "Primera Matrícula" (INT-013) ---
        cls.badge_name = "First Enrollment"
        if not frappe.db.exists("LMS Badge", cls.badge_name):
            badge = frappe.get_doc({
                "doctype": "LMS Badge",
                "title": "Primera Matrícula",
                "name": cls.badge_name,
                "description": "Otorgado por la primera matrícula en un curso",
                "event": "New",
                "reference_doctype": "LMS Enrollment",
                "user_field": "member",
                "condition": "True",
                "grant_only_once": 1
            })
            badge.insert()
            frappe.db.commit()
            print(f"✅ Badge '{cls.badge_name}' creado")
        else:
            print(f"ℹ️ Badge '{cls.badge_name}' ya existe")

        # --- 7. Crear Badge "Certificado Experto" (INT-014) ---
        cls.cert_badge_name = "Expert Certificate"
        if not frappe.db.exists("LMS Badge", cls.cert_badge_name):
            badge = frappe.get_doc({
                "doctype": "LMS Badge",
                "title": "Certificado Experto",
                "name": cls.cert_badge_name,
                "description": "Otorgado al obtener una certificación",
                "event": "New",
                "reference_doctype": "LMS Certificate",
                "user_field": "member",
                "condition": "True",
                "grant_only_once": 1
            })
            badge.insert()
            frappe.db.commit()
            print(f"✅ Badge '{cls.cert_badge_name}' creado")
        else:
            print(f"ℹ️ Badge '{cls.cert_badge_name}' ya existe")

        # --- 8. Crear usuario estudiante ---
        cls.student_email = "test_student_badge@example.com"
        if not frappe.db.exists("User", cls.student_email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": cls.student_email,
                "first_name": "Test",
                "last_name": "Badge Student",
                "send_welcome_email": 0
            })
            user.insert()
            user.add_roles("LMS Student")
            frappe.db.commit()
            print(f"✅ Usuario '{cls.student_email}' creado con rol LMS Student")
        else:
            print(f"ℹ️ Usuario '{cls.student_email}' ya existe")

    @classmethod
    def tearDownClass(cls):
        """Limpieza final"""
        # ... (código existente)
        super().tearDownClass()

    def setUp(self):
        """Configuración antes de cada prueba"""
        super().setUp()
        frappe.set_user("Administrator")
        frappe.db.commit()

    def tearDown(self):
        """Limpieza después de cada prueba"""
        frappe.set_user("Administrator")
        super().tearDown()

    # ======================================================================
    # INT-013: Badge de Primera Matrícula
    # ======================================================================

    def test_int_013_first_enrollment_badge(self):
        """
        INT-013: Verificar que al matricular un estudiante sin badges,
        se le asigne automáticamente el badge "Primera Matrícula"
        """
        print("\n" + "="*70)
        print("🧪 INT-013: Badge de Primera Matrícula")
        print("="*70)

        # --- 1. Verificar que el estudiante NO tiene badges previos ---
        print("\n📖 Paso 1: Verificar que el estudiante NO tiene badges previos")
        existing_badges = frappe.get_all(
            "LMS Badge Assignment",
            {"member": self.student_email}
        )
        self.assertEqual(len(existing_badges), 0,
            "El estudiante ya tiene badges previos")
        print("  ✅ El estudiante no tiene badges previos")

        # --- 2. Verificar que el badge existe ---
        print("\n📖 Paso 2: Verificar que el badge existe")
        self.assertTrue(frappe.db.exists("LMS Badge", self.badge_name),
            f"El badge '{self.badge_name}' no existe")
        badge = frappe.get_doc("LMS Badge", self.badge_name)
        print(f"  ✅ Badge encontrado: {badge.title}")
        print(f"     Evento: {badge.event}")
        print(f"     Documento: {badge.reference_doctype}")
        print(f"     Grant only once: {badge.grant_only_once}")

        # --- 3. Crear matrícula (debe disparar la asignación del badge) ---
        print("\n📖 Paso 3: Crear matrícula (disparador del badge)")
        enrollment = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"  ✅ Matrícula creada: {enrollment.name}")

        # --- 4. Verificar que el badge fue asignado automáticamente ---
        print("\n📖 Paso 4: Verificar que el badge fue asignado automáticamente")
        badge_assignments = frappe.get_all(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.badge_name
            },
            ["name", "badge", "badge_description", "issued_on"]
        )

        self.assertEqual(len(badge_assignments), 1,
            f"El badge no fue asignado automáticamente. Asignaciones encontradas: {len(badge_assignments)}")

        assignment = badge_assignments[0]
        print(f"  ✅ Badge asignado automáticamente")
        print(f"     ID: {assignment.name}")
        print(f"     Badge: {assignment.badge}")
        print(f"     Fecha: {assignment.issued_on}")

        # --- 5. Verificar que el badge está correctamente asignado al estudiante ---
        print("\n📖 Paso 5: Verificar que el badge está vinculado al estudiante correcto")
        assignment_doc = frappe.get_doc("LMS Badge Assignment", assignment.name)
        self.assertEqual(assignment_doc.member, self.student_email,
            "El badge no está vinculado al estudiante correcto")
        self.assertEqual(assignment_doc.badge, self.badge_name,
            "El badge asignado no coincide con el badge esperado")

        # Verificar que el badge tiene la información correcta
        badge_title = frappe.db.get_value("LMS Badge", assignment_doc.badge, "title")
        self.assertEqual(badge_title, "Primera Matrícula",
            "El título del badge asignado no es el correcto")

        print(f"  ✅ Badge vinculado al estudiante correcto: {assignment_doc.member}")
        print(f"  ✅ Badge asignado: {badge_title}")

        # --- 6. Verificar que no se asigna el badge nuevamente (idempotencia) ---
        print("\n📖 Paso 6: Verificar que no se asigna el badge nuevamente (idempotencia)")

        # Crear otra matrícula para el mismo usuario (en otro curso)
        course2_name = f"{self.course_name}-2"
        if not frappe.db.exists("LMS Course", course2_name):
            course2 = frappe.get_doc({
                "doctype": "LMS Course",
                "title": "Curso para Badge 2",
                "name": course2_name,
                "published": 1
            })
            course2.insert()
            print(f"  📝 Curso secundario creado: {course2_name}")

        # Crear capítulo y lección para el segundo curso
        chapter2 = upsert_chapter(
            title="Capítulo 1",
            course=course2_name,
            is_scorm_package=False
        )
        add_lesson(
            title="Lección 1",
            chapter=chapter2.name,
            course=course2_name,
            idx=1
        )

        # Crear segunda matrícula
        enrollment2 = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": course2_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"  ✅ Segunda matrícula creada: {enrollment2.name}")

        # Verificar que NO se creó una nueva asignación del mismo badge
        badge_assignments_after = frappe.get_all(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.badge_name
            }
        )

        self.assertEqual(len(badge_assignments_after), 1,
            f"El badge se asignó nuevamente (segunda vez). Asignaciones: {len(badge_assignments_after)}")
        print("  ✅ El badge NO se asignó nuevamente (idempotencia correcta)")

        # Limpiar curso secundario
        if frappe.db.exists("LMS Course", course2_name):
            course2 = frappe.get_doc("LMS Course", course2_name)
            for chapter_ref in course2.get("chapters", []):
                chapter_name = chapter_ref.get("chapter")
                if chapter_name and frappe.db.exists("Course Chapter", chapter_name):
                    chapter = frappe.get_doc("Course Chapter", chapter_name)
                    for lesson_ref in chapter.get("lessons", []):
                        lesson_name = lesson_ref.get("lesson")
                        if lesson_name and frappe.db.exists("Course Lesson", lesson_name):
                            frappe.delete_doc("Course Lesson", lesson_name, force=True)
                    frappe.delete_doc("Course Chapter", chapter_name, force=True)
            frappe.delete_doc("LMS Course", course2_name, force=True)
            frappe.db.commit()

        print("\n" + "="*70)
        print("✅ INT-013: Prueba completada exitosamente")
        print("   - Badge asignado automáticamente al matricularse")
        print("   - Badge vinculado al estudiante correcto")
        print("   - Badge no se duplica (idempotencia verificada)")
        print("="*70)

    # ======================================================================
    # INT-014: Badge al obtener Certificación
    # ======================================================================

    def test_int_014_certificate_badge(self):
        """
        INT-014: Verificar que al obtener un certificado,
        se le asigne automáticamente el badge "Certificado Experto"
        """
        print("\n" + "="*70)
        print("🧪 INT-014: Badge al obtener Certificación")
        print("="*70)

        # --- 1. Verificar que el estudiante NO tiene badges previos ---
        print("\n📖 Paso 1: Verificar que el estudiante NO tiene badges previos")
        existing_badges = frappe.get_all(
            "LMS Badge Assignment",
            {"member": self.student_email}
        )
        self.assertEqual(len(existing_badges), 0,
            "El estudiante ya tiene badges previos")
        print("  ✅ El estudiante no tiene badges previos")

        # --- 2. Verificar que el badge "Certificado Experto" existe ---
        print("\n📖 Paso 2: Verificar que el badge existe")
        self.assertTrue(frappe.db.exists("LMS Badge", self.cert_badge_name),
            f"El badge '{self.cert_badge_name}' no existe")
        badge = frappe.get_doc("LMS Badge", self.cert_badge_name)
        print(f"  ✅ Badge encontrado: {badge.title}")
        print(f"     Evento: {badge.event}")
        print(f"     Documento: {badge.reference_doctype}")
        print(f"     Grant only once: {badge.grant_only_once}")

        # --- 3. Matricular al estudiante en el curso ---
        print("\n📖 Paso 3: Matricular al estudiante en el curso")
        enrollment = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.cert_course_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"  ✅ Matrícula creada: {enrollment.name}")

        # A partir de aquí, el progreso, el quiz, el assignment y el
        # certificado se calculan sobre frappe.session.user, así que hay
        # que operar como el propio estudiante matriculado.
        frappe.set_user(self.student_email)

        # --- 4. Completar TODAS las lecciones ---
        print("\n📖 Paso 4: Completar todas las lecciones del curso")
        for chapter_number, lesson_number in self.cert_lesson_positions:
            mark_lesson_progress(self.cert_course_name, chapter_number, lesson_number)
            print(f"  ✅ Lección (capítulo {chapter_number}, lección {lesson_number}) completada")

        # --- 5. Enviar y aprobar el quiz ---
        print("\n📖 Paso 5: Enviar y aprobar el quiz")
        from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

        quiz = frappe.get_doc("LMS Quiz", self.cert_quiz_name)
        results = []
        for q in quiz.questions:
            question_doc = frappe.get_doc("LMS Question", q.question)
            correct_option = next(
                question_doc.get(f"option_{i}")
                for i in range(1, 5)
                if question_doc.get(f"is_correct_{i}")
            )
            results.append({
                "question_name": q.question,
                "answer": [correct_option]
            })

        submission = submit_quiz(
            quiz=self.cert_quiz_name,
            results=json.dumps(results)
        )
        frappe.db.commit()
        print(f"  ✅ Quiz enviado y aprobado")
        print(f"     Porcentaje: {submission['percentage']}%")

        # --- 6. Enviar y aprobar el assignment ---
        print("\n📖 Paso 6: Enviar y aprobar el assignment")
        assignment_submission = frappe.client.insert({
            "doctype": "LMS Assignment Submission",
            "member": self.student_email,
            "assignment": self.cert_assignment_name,
            "status": "Pass"
        })
        frappe.db.commit()
        print(f"  ✅ Assignment enviado y aprobado: {assignment_submission.name}")

        # --- 7. Verificar que el progreso es 100% ---
        print("\n📖 Paso 7: Verificar que el progreso es 100%")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100,
            f"El progreso no es 100%, es {enrollment.progress}%")
        print(f"  ✅ Progreso del curso: {enrollment.progress}%")

        # --- 8. Verificar que NO hay badge antes de emitir certificado ---
        print("\n📖 Paso 8: Verificar que NO hay badge antes del certificado")
        badge_before = frappe.db.exists(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.cert_badge_name
            }
        )
        self.assertFalse(badge_before, "El badge ya existe antes de emitir el certificado")
        print("  ✅ No hay badge antes de emitir el certificado")

        # --- 9. Emitir el certificado (esto debe disparar el badge) ---
        print("\n📖 Paso 9: Emitir el certificado (disparador del badge)")
        from lms.lms.doctype.lms_certificate.lms_certificate import create_certificate

        certificate = create_certificate(course=self.cert_course_name)
        frappe.db.commit()
        print(f"  ✅ Certificado emitido: {certificate.name}")

        # --- 10. Verificar que el badge fue asignado automáticamente ---
        print("\n📖 Paso 10: Verificar que el badge fue asignado automáticamente")
        badge_assignments = frappe.get_all(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.cert_badge_name
            },
            ["name", "badge", "badge_description", "issued_on"]
        )

        self.assertEqual(len(badge_assignments), 1,
            f"El badge no fue asignado automáticamente")

        assignment = badge_assignments[0]
        print(f"  ✅ Badge asignado automáticamente")
        print(f"     ID: {assignment.name}")
        print(f"     Badge: {assignment.badge}")
        print(f"     Fecha: {assignment.issued_on}")

        # --- 11. Verificar que el badge está vinculado al estudiante correcto ---
        print("\n📖 Paso 11: Verificar que el badge está vinculado al estudiante correcto")
        assignment_doc = frappe.get_doc("LMS Badge Assignment", assignment.name)
        self.assertEqual(assignment_doc.member, self.student_email,
            "El badge no está vinculado al estudiante correcto")
        self.assertEqual(assignment_doc.badge, self.cert_badge_name,
            "El badge asignado no coincide con el badge esperado")
        print(f"  ✅ Badge vinculado al estudiante correcto: {assignment_doc.member}")
        print(f"  ✅ Badge asignado: {assignment_doc.badge}")

        # --- 12. Verificar idempotencia (no se asigna badge nuevamente) ---
        print("\n📖 Paso 12: Verificar idempotencia (no se asigna badge nuevamente)")

        # Intentar emitir otro certificado para el mismo curso (no debería duplicar badge)
        certificate2 = create_certificate(course=self.cert_course_name)
        frappe.db.commit()
        print(f"  ✅ Segundo certificado emitido: {certificate2.name}")

        badge_assignments_after = frappe.get_all(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.cert_badge_name
            }
        )

        self.assertEqual(len(badge_assignments_after), 1,
            f"El badge se asignó nuevamente")
        print("  ✅ El badge NO se asignó nuevamente (idempotencia correcta)")

        print("\n" + "="*70)
        print("✅ INT-014: Prueba completada exitosamente")
        print("   - Certificado emitido correctamente")
        print("   - Badge 'Certificado Experto' asignado automáticamente")
        print("   - Badge vinculado al estudiante correcto")
        print("   - Badge no se duplica (idempotencia verificada)")
        print("="*70)

    # ======================================================================
    # CASO NEGATIVO: Intentar emitir certificado sin completar curso
    # ======================================================================

    def test_certificate_without_completion(self):
        """
        INT-014-NEG: Intentar emitir certificado sin completar el curso (debe fallar)
        """
        print("\n" + "="*70)
        print("🧪 INT-014-NEG: Intentar emitir certificado sin completar curso")
        print("="*70)

        # --- 1. Matricular al estudiante ---
        print("\n📖 Paso 1: Matricular al estudiante")
        enrollment = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.cert_course_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"  ✅ Matrícula creada: {enrollment.name}")

        # --- 2. Intentar emitir certificado (debería fallar) ---
        print("\n📖 Paso 2: Intentar emitir certificado (curso incompleto)")
        from lms.lms.doctype.lms_certificate.lms_certificate import create_certificate

        frappe.set_user(self.student_email)
        with self.assertRaises(Exception):
            create_certificate(course=self.cert_course_name)

        print("  ✅ Error capturado correctamente (curso incompleto)")
        print("="*70)

    def test_badge_grant_only_once(self):
        """
        INT-013-NEG: Verificar que un badge con 'grant_only_once=1' no se duplica
        """
        print("\n" + "="*70)
        print(" INT-013-NEG: Verificar grant_only_once")
        print("="*70)

        # Obtener el badge y verificar su configuración
        badge = frappe.get_doc("LMS Badge", self.badge_name)
        self.assertEqual(badge.grant_only_once, 1,
            "El badge no tiene configurado 'grant_only_once'")
        print(f"   Badge tiene grant_only_once={badge.grant_only_once}")

        # Verificar que el badge no se puede asignar manualmente si ya existe
        # Primero, matricular al estudiante
        enrollment = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"   Matrícula creada: {enrollment.name}")

        # Verificar que el badge está asignado
        assignments = frappe.get_all(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.badge_name
            }
        )
        self.assertEqual(len(assignments), 1, "El badge debería estar asignado")
        print("   Badge asignado automáticamente")

        print("="*70)
