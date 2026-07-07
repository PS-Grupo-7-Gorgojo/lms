"""
Pruebas de integración para Módulo 4: Matrículas y Progreso
Casos: INT-006 (Matrícula crea progreso automático)
"""

import frappe
from frappe.tests import IntegrationTestCase
from lms.lms.api import upsert_chapter, add_lesson


class TestEnrollmentProgress(IntegrationTestCase):
    """
    Prueba de integración para la relación Enrollment → Course Progress
    Verifica que al crear una matrícula, se cree automáticamente el progreso
    Usa frappe.client.insert() para simular la API cliente de Frappe
    """

    @classmethod
    def setUpClass(cls):
        """Configuración inicial: crear curso, capítulo, lección y usuario"""
        super().setUpClass()
        frappe.set_user("Administrator")

        # --- 1. Crear curso ---
        cls.course_name = "test-course-progress"
        if not frappe.db.exists("LMS Course", cls.course_name):
            course = frappe.get_doc({
                "doctype": "LMS Course",
                "title": "Curso para Progreso",
                "course_name": cls.course_name,
                "published": 1
            })
            course.insert()
            frappe.db.commit()
            print(f" Curso '{cls.course_name}' creado")

        # --- 2. Crear capítulo y lección ---
        chapter = upsert_chapter(
            title="Capítulo 1: Fundamentos",
            course=cls.course_name,
            is_scorm_package=False
        )
        cls.chapter_name = chapter.name
        print(f" Capítulo '{chapter.name}' creado")

        add_lesson(
            title="Lección 1: Introducción",
            chapter=cls.chapter_name,
            course=cls.course_name,
            idx=1
        )
        print(f" Lección creada en capítulo '{cls.chapter_name}'")

        # --- 3. Crear usuario estudiante ---
        cls.student_email = "test_student_progress@example.com"
        if not frappe.db.exists("User", cls.student_email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": cls.student_email,
                "first_name": "Test",
                "last_name": "Student Progress",
                "send_welcome_email": 0
            })
            user.insert()
            user.add_roles("LMS Student")
            frappe.db.commit()
            print(f" Usuario '{cls.student_email}' creado con rol LMS Student")

    @classmethod
    def tearDownClass(cls):
        """Limpieza final: eliminar curso, matrículas y progreso"""
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

        # Limpiar matrículas y progreso de pruebas anteriores
        if frappe.db.exists("LMS Enrollment", {"member": self.student_email, "course": self.course_name}):
            enrollment = frappe.get_doc("LMS Enrollment", {
                "member": self.student_email,
                "course": self.course_name
            })
            frappe.delete_doc("LMS Enrollment", enrollment.name, force=True)

        if frappe.db.exists("LMS Course Progress", {"member": self.student_email, "course": self.course_name}):
            progress = frappe.get_doc("LMS Course Progress", {
                "member": self.student_email,
                "course": self.course_name
            })
            frappe.delete_doc("LMS Course Progress", progress.name, force=True)

        frappe.db.commit()

    def tearDown(self):
        """Limpieza después de cada prueba"""
        super().tearDown()

    # ======================================================================
    # INT-006: Matrícula crea progreso automático
    # ======================================================================

    def test_int_006_enrollment_creates_progress(self):
        """
        INT-006: Verificar que al matricularse, se crea automáticamente el progreso
        Usa frappe.client.insert() para simular la API cliente de Frappe
        """
        print("\n" + "="*70)
        print(">  INT-006: Matrícula crea progreso automático")
        print("="*70)

        # --- 1. Verificar que el curso existe ---
        print("\n Paso 1: Verificar curso base")
        course = frappe.get_doc("LMS Course", self.course_name)
        self.assertIsNotNone(course)
        print(f"   Curso encontrado: {course.name}")

        # --- 2. Verificar que el usuario existe ---
        print("\n Paso 2: Verificar usuario estudiante")
        user = frappe.get_doc("User", self.student_email)
        self.assertIsNotNone(user)
        print(f"   Usuario encontrado: {user.email}")

        roles = frappe.get_roles(user.name)
        self.assertIn("LMS Student", roles)
        print("   Usuario tiene rol LMS Student")

        # --- 3. Verificar que NO existe progreso antes de la matrícula ---
        print("\n Paso 3: Verificar que NO existe progreso antes de matricular")
        progress_exists = frappe.db.exists(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name
            }
        )
        self.assertFalse(progress_exists, "El progreso ya existe antes de la matrícula")
        print("   No existe progreso antes de la matrícula")

        # --- 4. Crear matrícula usando frappe.client.insert() ---
        print("\n Paso 4: Crear matrícula (frappe.client.insert)")
        enrollment = frappe.client.insert({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name,
            "status": "Active"
        })
        frappe.db.commit()
        print(f"   Matrícula creada: {enrollment.name}")

        # --- 5. Verificar que se creó el progreso automáticamente ---
        print("\n Paso 5: Verificar que se creó progreso automáticamente")
        progress = frappe.db.get_value(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name
            },
            ["name", "status", "lesson"],
            as_dict=True
        )

        self.assertIsNotNone(progress,
            " No se creó automáticamente el registro de progreso al matricularse")
        print(f"   Progreso creado automáticamente: {progress.name}")
        print(f"   Status: {progress.status}")
        print(f"   Lección: {progress.lesson}")

        # --- 6. Verificar que el progreso tiene relación con el estudiante y curso ---
        print("\n Paso 6: Verificar relaciones del progreso")
        progress_doc = frappe.get_doc("LMS Course Progress", progress.name)

        self.assertEqual(progress_doc.member, self.student_email,
            "El progreso no está vinculado al estudiante correcto")
        self.assertEqual(progress_doc.course, self.course_name,
            "El progreso no está vinculado al curso correcto")

        print(f"   Progreso vinculado a estudiante: {progress_doc.member}")
        print(f"   Progreso vinculado a curso: {progress_doc.course}")

        print("\n" + "="*70)
        print(">  INT-006: Prueba completada exitosamente")
        print("   - Matrícula creada correctamente (via frappe.client.insert)")
        print("   - Progreso creado automáticamente")
        print("   - Progreso vinculado al estudiante y curso correctos")
        print("="*70)

    # ======================================================================
    # CASOS NEGATIVOS: Validación de errores
    # ======================================================================

    def test_enrollment_without_student(self):
        """
        INT-006-NEG: Intentar crear matrícula sin estudiante (debe fallar)
        """
        print("\n" + "="*70)
        print(">  INT-006-NEG: Crear matrícula sin estudiante")
        print("="*70)

        with self.assertRaises(Exception) as context:
            frappe.client.insert({
                "doctype": "LMS Enrollment",
                "course": self.course_name,
                "status": "Active"
            })

        self.assertIn("member", str(context.exception).lower())
        print("   Error capturado correctamente (campo member requerido)")
        print("="*70)

    def test_enrollment_without_course(self):
        """
        INT-006-NEG: Intentar crear matrícula sin curso (debe fallar)
        """
        print("\n" + "="*70)
        print(">  INT-006-NEG: Crear matrícula sin curso")
        print("="*70)

        with self.assertRaises(Exception) as context:
            frappe.client.insert({
                "doctype": "LMS Enrollment",
                "member": self.student_email,
                "status": "Active"
            })

        self.assertIn("course", str(context.exception).lower())
        print("  Error capturado correctamente (campo course requerido)")
        print("="*70)
