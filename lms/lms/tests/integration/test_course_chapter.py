"""
Pruebas de integración para Módulo 3: Cursos y Contenido
Casos: INT-003 (Creación jerarquía completa)
"""

import frappe
from frappe.tests import IntegrationTestCase
from lms.lms.api import upsert_chapter, add_lesson


class TestCourseChapterLesson(IntegrationTestCase):
    """
    Prueba de integración para la jerarquía Course → Chapter → Lesson
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        cls.course_name = "test-course-integration"
        if not frappe.db.exists("LMS Course", cls.course_name):
            course = frappe.get_doc({
                "doctype": "LMS Course",
                "title": "Curso de Prueba Integración",
                "course_name": cls.course_name,
                "published": 1
            })
            course.insert()
            frappe.db.commit()
            print(f"✅ Curso '{cls.course_name}' creado")

    @classmethod
    def tearDownClass(cls):
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

        super().tearDownClass()

    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")

    def tearDown(self):
        super().tearDown()

    # ======================================================================
    # INT-003: Course → Chapter → Lesson
    # ======================================================================

    def test_int_003_create_course_hierarchy(self):
        """
        INT-003: Verificar la creación completa de jerarquía Course → Chapter → Lesson
        """
        print("\n" + "="*70)
        print("🧪 INT-003: Creación de jerarquía Course → Chapter → Lesson")
        print("="*70)

        # --- 1. Verificar curso ---
        print("\n📖 Paso 1: Verificar curso base")
        course = frappe.get_doc("LMS Course", self.course_name)
        self.assertIsNotNone(course)
        print(f"  ✅ Curso encontrado: {course.name}")

        # --- 2. Crear capítulo ---
        print("\n📖 Paso 2: Crear capítulo dentro del curso")
        chapter = upsert_chapter(
            title="Capítulo 1: Fundamentos",
            course=self.course_name,
            is_scorm_package=False
        )

        self.assertIsNotNone(chapter.name)
        self.assertEqual(chapter.title, "Capítulo 1: Fundamentos")
        self.assertEqual(chapter.course, self.course_name)
        print(f"  ✅ Capítulo creado: {chapter.name}")

        # --- 3. Verificar relación Course → Chapter ---
        print("\n📖 Paso 3: Verificar relación Course → Chapter")
        course.reload()
        chapter_refs = [ref.chapter for ref in course.get("chapters", [])]
        self.assertIn(chapter.name, chapter_refs)
        print("  ✅ Capítulo linkeado al curso")

        # --- 4. Crear lección ---
        print("\n📖 Paso 4: Crear lección dentro del capítulo")
        lesson_title = "Lección 1: Introducción"
        add_lesson(
            title=lesson_title,
            chapter=chapter.name,
            course=self.course_name,
            idx=1
        )

        # --- 5. Verificar lección ---
        print("\n📖 Paso 5: Verificar lección creada")
        chapter.reload()
        lesson_refs = [ref.lesson for ref in chapter.get("lessons", [])]
        self.assertTrue(len(lesson_refs) > 0, "No se encontraron lecciones en el capítulo")
        lesson_name = lesson_refs[0]

        self.assertTrue(frappe.db.exists("Course Lesson", lesson_name))
        lesson = frappe.get_doc("Course Lesson", lesson_name)
        self.assertEqual(lesson.title, lesson_title)
        self.assertEqual(lesson.chapter, chapter.name)
        self.assertEqual(lesson.course, self.course_name)
        print(f"  ✅ Lección creada: {lesson.name}")

        # --- 6. Verificar relación Chapter → Lesson ---
        print("\n📖 Paso 6: Verificar relación Chapter → Lesson")
        chapter_lessons = [ref.lesson for ref in chapter.get("lessons", [])]
        self.assertIn(lesson_name, chapter_lessons)
        print("  ✅ Lección linkeada al capítulo")

        print("\n" + "="*70)
        print("✅ INT-003: Prueba completada exitosamente")
        print("="*70)

    # ======================================================================
    # CASOS NEGATIVOS
    # ======================================================================

    def test_create_chapter_without_title(self):
        """
        INT-003-NEG: Intentar crear capítulo sin título (debe fallar)
        """
        print("\n" + "="*70)
        print("🧪 INT-003-NEG: Crear capítulo sin título")
        print("="*70)

        with self.assertRaises(TypeError) as context:
            upsert_chapter(
                course=self.course_name,
                is_scorm_package=False
            )

        self.assertIn("title", str(context.exception).lower())
        print("  ✅ TypeError capturado correctamente")
        print("="*70)

    def test_create_chapter_without_course(self):
        """
        INT-003-NEG: Intentar crear capítulo sin curso (debe fallar)
        """
        print("\n" + "="*70)
        print("🧪 INT-003-NEG: Crear capítulo sin curso")
        print("="*70)

        with self.assertRaises(TypeError) as context:
            upsert_chapter(
                title="Capítulo sin curso",
                is_scorm_package=False
            )

        self.assertIn("course", str(context.exception).lower())
        print("  ✅ TypeError capturado correctamente")
        print("="*70)
