"""
Pruebas de integración para Módulo 4: Matrículas y Progreso
Casos: INT-006 (Completar lección crea progreso automático)
"""

import frappe
from frappe.tests import IntegrationTestCase
from lms.lms.test_helpers import BaseTestUtils


class TestEnrollmentProgress(BaseTestUtils):
    """
    Prueba de integración para la relación Enrollment → Course Progress
    Verifica que al completar la primera lección, se cree automáticamente el progreso
    """

    def setUp(self):
        """Configuración antes de CADA prueba"""
        super().setUp()
        frappe.set_user("Administrator")

        # --- 1. Crear curso ---
        self.course_title = f"Curso para Progreso {frappe.generate_hash(length=6)}"
        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": self.course_title,
            "course_name": self.course_title,
            "published": 1,
            "short_introduction": "Curso de prueba para progreso",
            "description": "Este curso se utiliza para probar el progreso automático"
        })
        course.append("instructors", {"instructor": "Administrator"})
        course.insert()
        self.course_name = course.name
        print(f" Curso '{self.course_title}' creado (ID: {self.course_name})")

        # --- 2. Crear capítulo CON referencia en el curso ---
        chapter = frappe.get_doc({
            "doctype": "Course Chapter",
            "title": "Capítulo 1: Fundamentos",
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
        print(f" Capítulo '{self.chapter_name}' creado y referenciado en el curso")

        # --- 3. Crear lección CON referencia en el capítulo ---
        lesson = frappe.get_doc({
            "doctype": "Course Lesson",
            "title": "Lección 1: Introducción",
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
        print(f" Lección '{self.lesson_name}' creada y referenciada en el capítulo")

        # --- 4. Crear usuario estudiante ---
        self.student_email = f"test_student_progress_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.student_email,
            "first_name": "Test",
            "last_name": "Student Progress",
            "send_welcome_email": 0
        })
        user.insert()
        user.add_roles("LMS Student")
        print(f" Usuario '{self.student_email}' creado con rol LMS Student")

    def tearDown(self):
        """Limpieza después de CADA prueba"""
        frappe.db.rollback()
        super().tearDown()

    # ======================================================================
    # INT-006: Completar lección crea progreso automático
    # ======================================================================

    def test_int_006_lesson_completion_creates_progress(self):
        """
        INT-006: Verificar que al completar la primera lección, se crea automáticamente el progreso
        """
        print("\n" + "="*70)
        print("🧪 INT-006: Completar lección crea progreso automático")
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
        print(f"     Matrícula creada: {enrollment.name}")

        # --- 2. Verificar que NO existe progreso después de la matrícula ---
        print("\nPaso 2: Verificar que NO existe progreso después de la matrícula")
        progress_after_enrollment = frappe.db.exists(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name
            }
        )
        self.assertFalse(progress_after_enrollment,
            "El progreso existe después de la matrícula (comportamiento incorrecto)")
        print("    No existe progreso después de la matrícula (comportamiento esperado)")

        # --- 3. Completar la primera lección ---
        print("\nPaso 3: Completar la primera lección")
        from lms.lms.doctype.course_lesson.course_lesson import save_progress

        frappe.set_user(self.student_email)
        result = save_progress(self.lesson_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección '{self.lesson_name}' completada (resultado: {result})")

        # --- 4. Verificar que el progreso se creó ---
        print("\nPaso 4: Verificar que el progreso se creó automáticamente")
        progress = frappe.db.get_value(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name
            },
            ["name", "status"],
            as_dict=True
        )

        self.assertIsNotNone(progress,
            "[x] No se creó automáticamente el registro de progreso al completar la lección")
        print(f"    Progreso creado automáticamente: {progress.name}")
        print(f"    Status: {progress.status}")

        # --- 5. Verificar relaciones ---
        print("\nPaso 5: Verificar relaciones del progreso")
        progress_doc = frappe.get_doc("LMS Course Progress", progress.name)

        self.assertEqual(progress_doc.member, self.student_email,
            "El progreso no está vinculado al estudiante correcto")
        self.assertEqual(progress_doc.course, self.course_name,
            "El progreso no está vinculado al curso correcto")
        self.assertEqual(progress_doc.lesson, self.lesson_name,
            "El progreso no está vinculado a la lección correcta")
        self.assertEqual(progress_doc.status, "Complete",
            "El estado del progreso no es 'Complete'")

        print(f"  (n.n) Progreso vinculado a estudiante: {progress_doc.member}")
        print(f"  (n.n) Progreso vinculado a curso: {progress_doc.course}")
        print(f"  (n.n) Progreso vinculado a lección: {progress_doc.lesson}")
        print(f"  (n.n) Estado: {progress_doc.status}")

        print("\n" + "="*70)
        print("(n.n) INT-006: Prueba completada exitosamente")
        print("="*70)


