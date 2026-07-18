"""
Pruebas de integración para Módulo 13: Caché e Invalidación
Casos: INT-026 (Course + Redis cache - Invalidación de caché al actualizar curso)
"""
import os
import unittest

import frappe
from frappe.tests import IntegrationTestCase

@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestCacheInvalidation(IntegrationTestCase):
    """
    Prueba de integración para verificar la invalidación de caché (Redis)
    al actualizar información de cursos en MariaDB.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.course_names_to_delete = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for course_name in cls.course_names_to_delete:
            if frappe.db.exists("LMS Course", course_name):
                frappe.delete_doc("LMS Course", course_name, force=True)
        frappe.db.commit()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        frappe.set_user("Administrator")

    def tearDown(self):
        super().tearDown()

    def create_test_course(self, title, course_name, published=1):
        if frappe.db.exists("LMS Course", course_name):
            frappe.delete_doc("LMS Course", course_name, force=True)
            frappe.db.commit()

        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": title,
            "course_name": course_name,
            "published": published,
            "short_introduction": "Curso de prueba de cache",
            "description": "Curso utilizado para pruebas de invalidación de caché",
        })
        course.append("instructors", {
            "instructor": "Administrator"
        })
        course.insert()
        frappe.db.commit()

        if course.name not in self.course_names_to_delete:
            self.course_names_to_delete.append(course.name)

        return course

    def test_int_026_cache_invalidation(self):
        """
        INT-026: Actualizar curso → invalidar caché
        """
        print("\n" + "="*70)
        print(" INT-026: Actualizar curso -> invalidar caché (Redis + MariaDB)")
        print("="*70)

        # Paso 1: Crear curso
        print("\nPaso 1: Crear curso de prueba en MariaDB")
        course_name = "test-cache-invalidation-course"
        course = self.create_test_course("Título Original Cache", course_name, published=1)
        self.assertIsNotNone(course)
        print(f"  Curso creado: '{course.name}' con título: '{course.title}'")

        # Paso 2: Cargar el curso en caché usando frappe.get_cached_value
        print("\nPaso 2: Cargar el título del curso en la caché de Redis")
        title_cached = frappe.get_cached_value("LMS Course", course.name, "title")
        self.assertEqual(title_cached, "Título Original Cache")
        print(f"  Valor almacenado en caché de Redis: '{title_cached}'")

        # Paso 3: Modificar el título del curso y guardar
        print("\nPaso 3: Modificar el título del curso y guardarlo en MariaDB")
        nuevo_titulo = "Nuevo Nombre Cache Invalidador"
        course.title = nuevo_titulo
        course.save()
        frappe.db.commit()
        print(f"  Curso actualizado y guardado en base de datos. Nuevo título: '{course.title}'")

        # Paso 4: Consulta inmediata para verificar invalidación automática de caché
        print("\nPaso 4: Realizar consulta inmediata para verificar invalidación de caché")
        # get_cached_value debe recuperar el nuevo valor de MariaDB (y re-cachearlo), no el valor viejo.
        title_after = frappe.get_cached_value("LMS Course", course.name, "title")
        self.assertEqual(
            title_after,
            nuevo_titulo,
            "La caché no se invalidó; se obtuvo el valor antiguo en lugar del actualizado."
        )
        print(f"  Confirmado: La caché se invalidó. Nuevo valor recuperado: '{title_after}'")

        print("\n" + "="*70)
        print("(n.n) INT-026: Prueba completada exitosamente")
        print("="*70)
