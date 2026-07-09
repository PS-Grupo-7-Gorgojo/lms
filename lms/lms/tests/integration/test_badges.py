"""
Pruebas de integración para Módulo 11: Badges / Gamificación
Casos: INT-013 (Badge de Primera Matrícula)
"""

import frappe
from frappe.tests import IntegrationTestCase


class TestBadgeEnrollment(IntegrationTestCase):
    """
    Prueba de integración para la asignación automática de badges
    Verifica que al matricular un estudiante sin badges, se le asigne el badge "Primera Matrícula"
    """

    def setUp(self):
        """Configuración antes de CADA prueba"""
        super().setUp()
        frappe.set_user("Administrator")

	    # Limpiar caché de badges para evitar referencias obsoletas
        frappe.cache_manager.clear_doctype_map("LMS Badge")
        frappe.cache().delete_key("doctype_map_LMS Badge")

	    # Limpiar badges antiguos
        frappe.db.delete("LMS Badge", {"title": ["like", "Primera Matrícula%"]})
        frappe.db.delete("LMS Badge", {"title": ["like", "Certificado Experto%"]})
        frappe.db.delete("LMS Badge Assignment", {"badge": ["like", "Primera Matrícula%"]})
        frappe.db.delete("LMS Badge Assignment", {"badge": ["like", "Certificado Experto%"]})
        frappe.db.commit()

        # --- 1. Crear curso ---
        self.course_title = f"Curso Badge {frappe.generate_hash(length=6)}"
        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": self.course_title,
            "published": 1,
            "short_introduction": "Curso para prueba de badge",
            "description": "Este curso se utiliza para probar la asignación de badges"
        })
        course.append("instructors", {"instructor": "Administrator"})
        course.insert()
        self.course_name = course.name
        print(f"Curso '{self.course_title}' creado (ID: {self.course_name})")

        # --- 2. Crear capítulo y lección ---
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

        # --- 3. Crear Badge "Primera Matrícula" ---
        badge_title = f"Primera Matrícula {frappe.generate_hash(length=6)}"
        badge = frappe.get_doc({
            "doctype": "LMS Badge",
            "title": badge_title,
            "description": "Otorgado por la primera matrícula en un curso",
            "image": "/assets/lms/images/badge-default.png",
            "event": "New",
            "reference_doctype": "LMS Enrollment",
            "user_field": "member",
            "condition": "doc.member != ''",
            "grant_only_once": 1,
            "enabled": 1
        })
        badge.insert()
        self.badge_name = badge.name
        frappe.db.commit()
        print(f"Badge '{self.badge_name}' creado")

        # --- 4. Crear usuario estudiante ---
        self.student_email = f"test_student_badge_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.student_email,
            "first_name": "Test",
            "last_name": "Badge Student",
            "send_welcome_email": 0
        })
        user.insert()
        user.add_roles("LMS Student")
        frappe.db.commit()
        print(f"Usuario '{self.student_email}' creado con rol LMS Student")

    def tearDown(self):
        """Limpieza después de CADA prueba"""
        # Eliminar asignaciones de badge
        if frappe.db.exists("LMS Badge Assignment", {"member": self.student_email}):
            assignments = frappe.get_all("LMS Badge Assignment", {"member": self.student_email})
            for assign in assignments:
                frappe.delete_doc("LMS Badge Assignment", assign.name, force=True)

        # Eliminar badge
        if frappe.db.exists("LMS Badge", self.badge_name):
            frappe.delete_doc("LMS Badge", self.badge_name, force=True)

        # Eliminar curso y sus dependencias
        if frappe.db.exists("LMS Course", self.course_name):
            course = frappe.get_doc("LMS Course", self.course_name)
            for chapter_ref in course.get("chapters", []):
                chapter_name = chapter_ref.get("chapter")
                if chapter_name and frappe.db.exists("Course Chapter", chapter_name):
                    chapter = frappe.get_doc("Course Chapter", chapter_name)
                    for lesson_ref in chapter.get("lessons", []):
                        lesson_name = lesson_ref.get("lesson")
                        if lesson_name and frappe.db.exists("Course Lesson", lesson_name):
                            frappe.delete_doc("Course Lesson", lesson_name, force=True)
                    frappe.delete_doc("Course Chapter", chapter_name, force=True)
            frappe.delete_doc("LMS Course", self.course_name, force=True)
            frappe.db.commit()

        # Eliminar usuario
        if frappe.db.exists("User", self.student_email):
            frappe.delete_doc("User", self.student_email, force=True)
            frappe.db.commit()

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
        print(">  INT-013: Badge de Primera Matrícula")
        print("="*70)

        # --- 1. Verificar que el estudiante NO tiene badges previos ---
        print("\nPaso 1: Verificar que el estudiante NO tiene badges previos")
        existing_badges = frappe.get_all(
            "LMS Badge Assignment",
            {"member": self.student_email}
        )
        self.assertEqual(len(existing_badges), 0,
            "El estudiante ya tiene badges previos")
        print("    El estudiante no tiene badges previos")

        # --- 2. Verificar que el badge existe ---
        print("\nPaso 2: Verificar que el badge existe")
        self.assertTrue(frappe.db.exists("LMS Badge", self.badge_name),
            f"El badge '{self.badge_name}' no existe")
        badge = frappe.get_doc("LMS Badge", self.badge_name)
        print(f"  Badge encontrado: {badge.title}")
        print(f"     Evento: {badge.event}")
        print(f"     Documento: {badge.reference_doctype}")
        print(f"     Campo usuario: {badge.user_field}")
        print(f"     Condition: {badge.condition}")
        print(f"     Grant only once: {badge.grant_only_once}")

        # --- 3. Crear matrícula ---
        print("\nPaso 3: Crear matrícula (disparador del badge)")
        enrollment = frappe.get_doc({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name
        })
        enrollment.flags.ignore_links = True
        enrollment.insert()
        frappe.db.commit()
        print(f"    Matrícula creada: {enrollment.name}")

        # --- 4. Verificar que el badge fue asignado automáticamente ---
        print("\nPaso 4: Verificar que el badge fue asignado automáticamente")
        badge_assignments = frappe.get_all(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.badge_name
            },
            ["name", "badge", "issued_on", "owner"]
        )

        self.assertEqual(len(badge_assignments), 1,
            f"El badge no fue asignado automáticamente. Asignaciones encontradas: {len(badge_assignments)}")

        assignment = badge_assignments[0]
        badge_title = frappe.db.get_value("LMS Badge", assignment.badge, "title")

        print(f"  Badge asignado automáticamente")
        print(f"     ID: {assignment.name}")
        print(f"     Badge: {badge_title}")
        print(f"     Fecha: {assignment.issued_on}")
        print(f"     Otorgado por: {assignment.owner}")

        # --- 5. Verificar que el badge está correctamente asignado ---
        print("\nPaso 5: Verificar que el badge está vinculado al estudiante correcto")
        assignment_doc = frappe.get_doc("LMS Badge Assignment", assignment.name)
        self.assertEqual(assignment_doc.member, self.student_email,
            "El badge no está vinculado al estudiante correcto")
        self.assertEqual(assignment_doc.badge, self.badge_name,
            "El badge asignado no coincide con el badge esperado")

        print(f"   Badge vinculado al estudiante correcto: {assignment_doc.member}")
        print(f"   Badge asignado: {badge_title}")

        print("\n" + "="*70)
        print("(n.n) INT-013: Prueba completada exitosamente")
        print("="*70)

	# ======================================================================
	# INT-014: Badge al obtener Certificación
	# ======================================================================

    def test_int_014_certificate_badge(self):
	    """INT-014: Badge al obtener Certificación"""
	    print("\n" + "="*70)
	    print(">  INT-014: Badge al obtener Certificación")
	    print("="*70)

	    # --- 1. Crear Badge "Certificado Experto" ---
	    badge_title = f"Certificado Experto {frappe.generate_hash(length=6)}"
	    badge = frappe.get_doc({
	        "doctype": "LMS Badge",
	        "title": badge_title,
	        "description": "Otorgado al obtener una certificación",
	        "image": "/assets/lms/images/badge-default.png",
	        "event": "New",
	        "reference_doctype": "LMS Certificate",
	        "user_field": "member",
	        "condition": "doc.member != ''",
	        "grant_only_once": 1,
	        "enabled": 1
	    })
	    badge.insert()
	    self.cert_badge_name = badge.name
	    frappe.db.commit()
	    print(f"Badge '{self.cert_badge_name}' creado")

	    # --- 2. Crear curso con certificación ---
	    course_title = f"Curso Certificado Badge {frappe.generate_hash(length=6)}"
	    course = frappe.get_doc({
	        "doctype": "LMS Course",
	        "title": course_title,
	        "published": 1,
	        "enable_certification": 1,
	        "short_introduction": "Curso para badge de certificado",
	        "description": "Este curso se utiliza para probar la asignación de badge al obtener certificado"
	    })
	    course.append("instructors", {"instructor": "Administrator"})
	    course.insert()
	    self.cert_course_name = course.name
	    frappe.db.commit()
	    print(f"Curso '{course_title}' creado (ID: {self.cert_course_name})")

	    # --- 3. Crear capítulo ---
	    chapter = frappe.get_doc({
	        "doctype": "Course Chapter",
	        "title": "Capítulo 1",
	        "course": self.cert_course_name,
	        "is_scorm_package": 0
	    })
	    chapter.flags.ignore_links = True
	    chapter.insert()

	    chapter_ref = frappe.get_doc({
	        "doctype": "Chapter Reference",
	        "chapter": chapter.name,
	        "parent": self.cert_course_name,
	        "parenttype": "LMS Course",
	        "parentfield": "chapters",
	        "idx": 1
	    })
	    chapter_ref.flags.ignore_links = True
	    chapter_ref.insert()
	    frappe.db.commit()

	    # --- 4. Crear Lección 1 ---
	    lesson1 = frappe.get_doc({
	        "doctype": "Course Lesson",
	        "title": "Lección 1: Introducción",
	        "chapter": chapter.name,
	        "course": self.cert_course_name
	    })
	    lesson1.flags.ignore_links = True
	    lesson1.insert()
	    self.cert_lesson1_name = lesson1.name

	    lesson_ref1 = frappe.get_doc({
	        "doctype": "Lesson Reference",
	        "lesson": lesson1.name,
	        "parent": chapter.name,
	        "parenttype": "Course Chapter",
	        "parentfield": "lessons",
	        "idx": 1
	    })
	    lesson_ref1.flags.ignore_links = True
	    lesson_ref1.insert()
	    frappe.db.commit()

	    # --- 5. Crear preguntas para el quiz ---
	    question_names = []
	    questions_data = [
	        {
	            "question": "¿Qué se obtiene al completar el curso?",
	            "type": "Choices",
	            "option_1": "Un badge",
	            "option_2": "Un certificado",
	            "option_3": "Ambos",
	            "is_correct_1": 0,
	            "is_correct_2": 0,
	            "is_correct_3": 1
	        },
	        {
	            "question": "¿Qué porcentaje se necesita para aprobar?",
	            "type": "Choices",
	            "option_1": "50%",
	            "option_2": "70%",
	            "option_3": "100%",
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
	        question_names.append(q.name)
	    frappe.db.commit()

	    # --- 6. Crear quiz sin especificar "name" ---
	    quiz = frappe.get_doc({
	        "doctype": "LMS Quiz",
	        "title": "Quiz para Badge de Certificado",
	        "passing_percentage": 70,
	        "course": self.cert_course_name,
	        "max_attempts": 0,
	        "total_marks": 10
	    })
	    quiz.insert()

	    # Guardar el nombre REAL generado por Frappe
	    quiz_name = quiz.name
	    print(f"Quiz creado con nombre REAL: {quiz_name}")

	    # Agregar preguntas al quiz
	    for q_name in question_names:
	        quiz.append("questions", {
	            "question": q_name,
	            "marks": 5
	        })
	    quiz.save()
	    frappe.db.commit()
	    self.cert_quiz_name = quiz_name

	    # --- 7. Crear Lección 2 (con quiz) usando el nombre REAL ---
	    lesson2 = frappe.get_doc({
	        "doctype": "Course Lesson",
	        "title": "Lección 2: Evaluación",
	        "chapter": chapter.name,
	        "course": self.cert_course_name,
	        "content": frappe.as_json({
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
	    lesson2.flags.ignore_links = True
	    lesson2.insert()
	    self.cert_lesson2_name = lesson2.name

	    lesson_ref2 = frappe.get_doc({
	        "doctype": "Lesson Reference",
	        "lesson": lesson2.name,
	        "parent": chapter.name,
	        "parenttype": "Course Chapter",
	        "parentfield": "lessons",
	        "idx": 2
	    })
	    lesson_ref2.flags.ignore_links = True
	    lesson_ref2.insert()
	    frappe.db.commit()

	    # --- 8. Crear Assignment ---
	    assignment_name = f"test-assignment-cert-badge-{frappe.generate_hash(length=6)}"
	    assignment = frappe.get_doc({
	        "doctype": "LMS Assignment",
	        "title": "Assignment para Badge de Certificado",
	        "name": assignment_name,
	        "course": self.cert_course_name,
	        "lesson": lesson2.name,
	        "type": "Text",
	        "question": "Describe el proceso de certificación en tus propias palabras."
	    })
	    assignment.insert()
	    frappe.db.commit()
	    self.cert_assignment_name = assignment_name
	    print(f"Curso con capítulos, lecciones, quiz y assignment creados")

	    # --- 9. Crear usuario estudiante ---
	    student_email = f"test_student_cert_badge_{frappe.generate_hash(length=6)}@example.com"
	    user = frappe.get_doc({
	        "doctype": "User",
	        "email": student_email,
	        "first_name": "Test",
	        "last_name": "Cert Badge Student",
	        "send_welcome_email": 0
	    })
	    user.insert()
	    user.add_roles("LMS Student")
	    frappe.db.commit()
	    self.cert_student_email = student_email
	    print(f"Usuario '{student_email}' creado con rol LMS Student")

	    # --- 10. Verificar NO tiene badges ---
	    print("\nPaso 1: Verificar que el estudiante NO tiene badges previos")
	    existing_badges = frappe.get_all("LMS Badge Assignment", {"member": student_email})
	    self.assertEqual(len(existing_badges), 0)
	    print("    El estudiante no tiene badges previos")

	    # --- 11. Matricular ---
	    print("\nPaso 2: Crear matrícula")
	    enrollment = frappe.get_doc({
	        "doctype": "LMS Enrollment",
	        "member": student_email,
	        "course": self.cert_course_name
	    })
	    enrollment.flags.ignore_links = True
	    enrollment.insert()
	    frappe.db.commit()
	    print(f"    Matrícula creada: {enrollment.name}")

	    # --- 12. Completar curso ---
	    print("\nPaso 3: Completar curso")
	    from lms.lms.doctype.course_lesson.course_lesson import save_progress
	    from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz

	    frappe.set_user(student_email)

	    save_progress(lesson1.name, self.cert_course_name)
	    frappe.db.commit()
	    print("    Lección 1 completada")

	    # Quiz
	    results_high = [
	        {"question_name": question_names[0], "answer": ["Ambos"]},
	        {"question_name": question_names[1], "answer": ["70%"]}
	    ]
	    submission = submit_quiz(quiz=quiz_name, results=frappe.as_json(results_high))
	    frappe.db.commit()
	    print("    Quiz enviado y aprobado")

	    # Assignment
	    assignment_submission = frappe.get_doc({
	        "doctype": "LMS Assignment Submission",
	        "member": student_email,
	        "assignment": assignment_name,
	        "lesson": lesson2.name,
	        "type": "Text",
	        "answer": "El proceso de certificación requiere completar todas las lecciones.",
	        "status": "Pass"
	    })
	    assignment_submission.flags.ignore_links = True
	    assignment_submission.insert()
	    frappe.db.commit()
	    print("    Assignment enviado y aprobado")

	    save_progress(lesson2.name, self.cert_course_name)
	    frappe.db.commit()
	    print("    Lección 2 completada")

	    enrollment.reload()
	    self.assertEqual(enrollment.progress, 100)
	    print(f"    Progreso del curso: {enrollment.progress}%")

	    # --- 13. Emitir certificado ---
	    print("\nPaso 4: Emitir certificado")
	    frappe.set_user("Administrator")

	    template = frappe.db.get_value("Print Format", {"doc_type": "LMS Certificate"}, "name")

	    certificate = frappe.get_doc({
	        "doctype": "LMS Certificate",
	        "member": student_email,
	        "course": self.cert_course_name,
	        "issue_date": frappe.utils.nowdate(),
	        "published": 1,
	        "template": template,
	    })
	    certificate.insert(ignore_permissions=True)
	    frappe.db.commit()
	    print(f"    Certificado emitido: {certificate.name}")

	    # --- 14. Verificar badge ---
	    print("\nPaso 5: Verificar que el badge fue asignado automáticamente")
	    badge_assignments = frappe.get_all(
	        "LMS Badge Assignment",
	        {"member": student_email, "badge": self.cert_badge_name},
	        ["name", "badge", "issued_on", "owner"]
	    )
	    self.assertEqual(len(badge_assignments), 1)

	    assignment = badge_assignments[0]
	    badge_title = frappe.db.get_value("LMS Badge", assignment.badge, "title")

	    print(f"  Badge asignado automáticamente")
	    print(f"     Badge: {badge_title}")
	    print(f"     Fecha: {assignment.issued_on}")

	    assignment_doc = frappe.get_doc("LMS Badge Assignment", assignment.name)
	    self.assertEqual(assignment_doc.member, student_email)
	    self.assertEqual(assignment_doc.badge, self.cert_badge_name)

	    print("\n" + "="*70)
	    print("(n.n)  INT-014: Prueba completada exitosamente")
	    print("="*70)

    # ======================================================================
    # CASO NEGATIVO
    # ======================================================================

    def test_badge_not_assigned_without_enrollment(self):
        """
        INT-013-NEG: Verificar que el badge NO se asigna sin matrícula
        """
        print("\n" + "="*70)
        print(">  INT-013-NEG: Badge no asignado sin matrícula")
        print("="*70)

        # Verificar que el badge NO fue asignado (no hay matrícula)
        badge_assignments = frappe.get_all(
            "LMS Badge Assignment",
            {
                "member": self.student_email,
                "badge": self.badge_name
            },
            ["name", "badge", "issued_on", "owner"]
        )
        self.assertEqual(len(badge_assignments), 0,
            "El badge fue asignado sin matrícula")
        print("   Badge no asignado (no hay matrícula)")

        print("="*70)
