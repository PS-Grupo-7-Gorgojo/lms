"""
Pruebas de integración para Cadena Completa de Eventos
Casos: INT-027 (Course + Enrollment + Badge + Index - Cadena completa)
"""

import os
import unittest

import frappe
from frappe.tests import IntegrationTestCase
from lms.lms.doctype.course_lesson.course_lesson import save_progress


@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestIntegrationChain(IntegrationTestCase):
    """
    Prueba de integración para la cadena completa de eventos:
    Crear curso → Matricular usuario → Completar lección → Badge asignado → Índice actualizado
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        # Limpiar caché de badges
        frappe.cache_manager.clear_doctype_map("LMS Badge")
        frappe.cache().delete_key("doctype_map_LMS Badge")

        # Limpiar badges antiguos
        frappe.db.delete("LMS Badge", {"title": ["like", "Primera Matrícula%"]})
        frappe.db.delete("LMS Badge", {"title": ["like", "Certificado Experto%"]})
        frappe.db.delete("LMS Badge Assignment", {"badge": ["like", "Primera Matrícula%"]})
        frappe.db.delete("LMS Badge Assignment", {"badge": ["like", "Certificado Experto%"]})
        frappe.db.commit()

    def setUp(self):
        """Configuración antes de CADA prueba"""
        super().setUp()
        frappe.set_user("Administrator")

        # --- 1. Crear curso ---
        self.course_title = f"Curso Chain {frappe.generate_hash(length=6)}"
        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": self.course_title,
            "published": 1,
            "short_introduction": "Curso para prueba de cadena completa",
            "description": "Este curso se utiliza para probar la cadena completa de eventos"
        })
        course.append("instructors", {"instructor": "Administrator"})
        course.insert()
        self.course_name = course.name
        print(f" Curso '{self.course_title}' creado (ID: {self.course_name})")

        # --- 2. Crear capítulo ---
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

        # --- 3. Crear lección ---
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
        print(f" Capítulo y lección creados")

        # --- 4. Crear Badge "Primera Matrícula" (se dispara al matricular) ---
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
        print(f" Badge '{self.badge_name}' creado")
        print(f"   Evento: {badge.event}")
        print(f"   Disparador: {badge.reference_doctype}")

        # --- 5. Crear usuario estudiante ---
        self.student_email = f"test_student_chain_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.student_email,
            "first_name": "Test",
            "last_name": "Chain Student",
            "send_welcome_email": 0
        })
        user.insert()
        user.add_roles("LMS Student")
        frappe.db.commit()
        print(f" Usuario '{self.student_email}' creado con rol LMS Student")

    def tearDown(self):
	    """Limpieza después de CADA prueba"""
	    frappe.set_user("Administrator")

	    # Eliminar matrículas, esto dispara hooks que necesitan el badge
	    if frappe.db.exists("LMS Enrollment", {"member": self.student_email, "course": self.course_name}):
	        enrollment = frappe.get_doc("LMS Enrollment", {
	            "member": self.student_email,
	            "course": self.course_name
	        })
	        frappe.delete_doc("LMS Enrollment", enrollment.name, force=True, ignore_permissions=True)

	    # Eliminar asignaciones de badge
	    if frappe.db.exists("LMS Badge Assignment", {"member": self.student_email}):
	        assignments = frappe.get_all("LMS Badge Assignment", {"member": self.student_email})
	        for assign in assignments:
	            frappe.delete_doc("LMS Badge Assignment", assign.name, force=True, ignore_permissions=True)

	    # Eliminar el badge
	    if frappe.db.exists("LMS Badge", self.badge_name):
	        frappe.delete_doc("LMS Badge", self.badge_name, force=True, ignore_permissions=True)

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
	                        frappe.delete_doc("Course Lesson", lesson_name, force=True, ignore_permissions=True)
	                frappe.delete_doc("Course Chapter", chapter_name, force=True, ignore_permissions=True)
	        frappe.delete_doc("LMS Course", self.course_name, force=True, ignore_permissions=True)
	        frappe.db.commit()

	    # Eliminar usuario
	    if frappe.db.exists("User", self.student_email):
	        frappe.delete_doc("User", self.student_email, force=True, ignore_permissions=True)
	        frappe.db.commit()

	    super().tearDown()

    # ======================================================================
    # INT-028: Cadena completa de eventos encadenados
    # ======================================================================

    def test_int_028_complete_integration_chain(self):
        """
        INT-028: Cadena completa: crear curso → matricular usuario →
        completar lección → badge → índice actualizado
        """
        print("\n" + "="*70)
        print("> INT-028: Cadena completa de eventos encadenados")
        print("="*70)

        # --- 1. Verificar curso creado ---
        print("\nPaso 1: Verificar curso")
        course = frappe.get_doc("LMS Course", self.course_name)
        self.assertIsNotNone(course)
        print(f"    Curso encontrado: {course.name}")

        # --- 2. Matricular estudiante (esto dispara el badge) ---
        print("\nPaso 2: Matricular estudiante (dispara badge)")
        enrollment = frappe.get_doc({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name
        })
        enrollment.flags.ignore_links = True
        enrollment.insert()
        frappe.db.commit()
        print(f"    Matrícula creada: {enrollment.name}")

        # --- 3. Verificar badge asignado al matricularse ---
        print("\nPaso 3: Verificar badge asignado al matricularse")
        badge_assignments = frappe.get_all(
            "LMS Badge Assignment",
            {"member": self.student_email, "badge": self.badge_name},
            ["name", "badge", "issued_on", "owner"]
        )
        self.assertEqual(len(badge_assignments), 1,
            "El badge no se asignó al crear la matrícula")
        assignment = badge_assignments[0]
        badge_title = frappe.db.get_value("LMS Badge", assignment.badge, "title")
        print(f"    Badge asignado al matricularse: {badge_title}")
        print(f"     Fecha: {assignment.issued_on}")
        print(f"     Otorgado por: {assignment.owner}")

        # --- 4. Completar la lección ---
        print("\nPaso 4: Completar la lección")
        frappe.set_user(self.student_email)
        result = save_progress(self.lesson_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección completada (resultado: {result})")

        # --- 5. Verificar progreso 100% ---
        print("\nPaso 5: Verificar progreso 100%")
        enrollment.reload()
        self.assertEqual(enrollment.progress, 100)
        print(f"    Progreso del curso: {enrollment.progress}%")

        # --- 6. Actualizar título del curso (como Administrator) ---
        print("\nPaso 6: Actualizar título del curso")
        # Cambiar a Administrator para tener permisos
        frappe.set_user("Administrator")

        nuevo_titulo = f"Nuevo Curso Chain {frappe.generate_hash(length=6)}"
        course = frappe.get_doc("LMS Course", self.course_name)
        course.title = nuevo_titulo
        course.save()
        frappe.db.commit()
        print(f"    Título actualizado a: {nuevo_titulo}")

        # --- 7. Reconstruir índice de búsqueda ---
        print("\nPaso 7: Reconstruir índice de búsqueda")
        from lms.sqlite import build_index
        build_index()
        print("    Índice de búsqueda reconstruido")

        # --- 8. Verificar que el curso aparece con el nuevo título ---
        print("\nPaso 8: Buscar por nuevo título")
        from lms.sqlite import LearningSearch
        search = LearningSearch()
        search_term = nuevo_titulo.split()[0]
        results = search.search(search_term)
        course_names = [r["name"] for r in results.get("results", []) if r["doctype"] == "LMS Course"]
        self.assertIn(self.course_name, course_names,
            f"El curso '{self.course_name}' no fue encontrado por el nuevo título '{search_term}'")
        print(f"    Curso encontrado por el nuevo título: '{search_term}'")

        # --- 9. Verificar que NO aparece con el título anterior ---
        print("\nPaso 9: Buscar por título anterior (no debe encontrar)")
        results_old = search.search(self.course_title)
        course_names_old = [r["name"] for r in results_old.get("results", []) if r["doctype"] == "LMS Course"]
        self.assertNotIn(self.course_name, course_names_old,
            f"El curso '{self.course_name}' aún aparece con el título antiguo '{self.course_title}'")
        print(f"    Curso NO aparece con el título antiguo: '{self.course_title}'")

        print("\n" + "="*70)
        print("  INT-028: Prueba completada exitosamente")
        print("   - Curso creado correctamente")
        print("   - Estudiante matriculado")
        print("   - Badge asignado al matricularse")
        print("   - Lección completada (progreso 100%)")
        print("   - Índice de búsqueda actualizado")
        print("   - Curso encontrado por nuevo título")
        print("   - Curso NO encontrado por título antiguo")
        print("="*70)

    # ======================================================================
    # CASO NEGATIVO: Sin badge sin matrícula
    # ======================================================================

    def test_int_028_no_badge_without_enrollment(self):
        """
        INT-028-NEG: Verificar que NO se asigna badge sin matrícula
        """
        print("\n" + "="*70)
        print("🧪 INT-028-NEG: Sin badge sin matrícula")
        print("="*70)

        # --- 1. Verificar que NO hay matrícula ---
        print("\nPaso 1: Verificar que no hay matrícula")
        enrollment_exists = frappe.db.exists(
            "LMS Enrollment",
            {"member": self.student_email, "course": self.course_name}
        )
        self.assertFalse(enrollment_exists)
        print("    No hay matrícula")

        # --- 2. Verificar que NO hay badge ---
        print("\nPaso 2: Verificar que NO hay badge")
        badge_assignments = frappe.get_all(
            "LMS Badge Assignment",
            {"member": self.student_email, "badge": self.badge_name}
        )
        self.assertEqual(len(badge_assignments), 0)
        print("    No hay badge asignado (sin matrícula)")

        print("\n" + "="*70)
        print("(n.n) INT-028-NEG: Prueba completada exitosamente")
        print("="*70)

