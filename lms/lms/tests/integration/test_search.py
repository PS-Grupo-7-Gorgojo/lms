"""
Pruebas de integración para Módulo 13: Búsqueda y SQLite Index
Casos: INT-017 (Course + MariaDB Index - Actualizar curso → índice actualizado)
       INT-018 (MariaDB Index + Migración - Índice se reconstruye tras migración)
"""
import os
import unittest

import frappe
from frappe.tests import IntegrationTestCase

@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestSearchIntegration(IntegrationTestCase):
    """
    Prueba de integración para la búsqueda SQLite (LearningSearch) y su sincronización con MariaDB
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.course_names_to_delete = []

    @classmethod
    def tearDownClass(cls):
        # Limpieza de cursos de prueba creados
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
        """
        Helper para crear un curso de prueba con todos los campos requeridos
        """
        if frappe.db.exists("LMS Course", course_name):
            frappe.delete_doc("LMS Course", course_name, force=True)
            frappe.db.commit()

        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": title,
            "course_name": course_name,
            "published": published,
            "short_introduction": "Curso introductorio de prueba para búsqueda",
            "description": "Curso completo para probar la indexación de búsqueda SQLite",
        })
        course.append("instructors", {
            "instructor": "Administrator"
        })
        course.insert()
        frappe.db.commit()

        if course.name not in self.course_names_to_delete:
            self.course_names_to_delete.append(course.name)

        return course

    # ======================================================================
    # INT-017: Crear/modificar curso → índice actualizado
    # ======================================================================

    def test_int_017_create_modify_course_updates_index(self):
        """
        INT-017: Crear/modificar curso → índice actualizado
        Verifica que al crear/modificar un curso en MariaDB, tras regenerar el índice,
        la búsqueda devuelva el curso con la información actualizada.
        """
        print("\n" + "="*70)
        print(" INT-017: Crear/modificar curso -> índice actualizado")
        print("="*70)

        # Paso 1: Crear curso con título inicial
        print("\nPaso 1: Crear curso con título inicial")
        title_initial = "Curso de Cocina Italiana de Prueba"
        name_initial = "curso-cocina-italiana-prueba"
        course = self.create_test_course(title_initial, name_initial, published=1)
        self.assertIsNotNone(course)
        print(f"  Curso creado: '{course.name}' con título: '{course.title}'")

        # Paso 2: Reconstruir índice SQLite
        print("\nPaso 2: Reconstruir el índice SQLite")
        from lms.sqlite import build_index
        build_index()
        print("  Índice reconstruido")

        # Paso 3: Buscar por el título inicial
        print("\nPaso 3: Buscar curso por su título inicial")
        from lms.sqlite import LearningSearch
        search = LearningSearch()
        res = search.search("Cocina Italiana")
        course_names = [r["name"] for r in res.get("results", []) if r["doctype"] == "LMS Course"]
        self.assertIn(course.name, course_names, f"El curso '{course.name}' no fue encontrado por el término 'Cocina Italiana'")
        print(f"  Confirmado: Curso encontrado usando el título inicial")

        # Paso 4: Modificar el título del curso
        print("\nPaso 4: Modificar el título del curso en MariaDB")
        title_new = "Curso de Repostería Francesa de Prueba"
        course.title = title_new
        course.save()
        frappe.db.commit()
        print(f"  Título actualizado a: '{course.title}'")

        # Paso 5: Reconstruir el índice SQLite para sincronizar la actualización
        print("\nPaso 5: Reconstruir el índice SQLite tras la actualización")
        build_index()
        print("  Índice reconstruido")

        # Paso 6: Buscar por el nuevo título
        print("\nPaso 6: Buscar curso por el nuevo título")
        res_new = search.search("Repostería Francesa")
        course_names_new = [r["name"] for r in res_new.get("results", []) if r["doctype"] == "LMS Course"]
        self.assertIn(course.name, course_names_new, f"El curso '{course.name}' no fue encontrado por el nuevo término 'Repostería Francesa'")
        print(f"  Confirmado: Curso encontrado usando el nuevo título")

        # Paso 7: Buscar por el título anterior (debería no encontrar este curso)
        print("\nPaso 7: Buscar curso por el título antiguo")
        res_old = search.search("Cocina Italiana")
        course_names_old = [r["name"] for r in res_old.get("results", []) if r["doctype"] == "LMS Course"]
        self.assertNotIn(course.name, course_names_old, f"El curso '{course.name}' todavía se encuentra con el título antiguo")
        print(f"  Confirmado: El curso ya no se encuentra con el título antiguo")

        print("\n" + "="*70)
        print("(n.n) INT-017: Prueba completada exitosamente")
        print("="*70)

    # ======================================================================
    # INT-018: Índice se reconstruye tras migración
    # ======================================================================

    def test_int_018_after_migrate_rebuilds_index(self):
        """
        INT-018: Índice se reconstruye tras migración
        Verifica que el hook 'after_migrate' esté correctamente configurado y que al ejecutarse
        sincronice el índice de búsqueda con la base de datos MariaDB de forma consistente.
        """
        print("\n" + "="*70)
        print(" INT-018: Índice se reconstruye tras migración")
        print("="*70)

        # Paso 1: Verificar el registro de la función en hooks.py bajo 'after_migrate'
        print("\nPaso 1: Verificar registro de 'after_migrate' en hooks.py")
        hooks = frappe.get_hooks("after_migrate")
        self.assertIn(
            "lms.sqlite.build_index_in_background",
            hooks,
            "El hook 'lms.sqlite.build_index_in_background' no está registrado en hooks.py under 'after_migrate'"
        )
        print("  Hook de migración registrado correctamente en hooks.py")

        # Paso 2: Crear un curso nuevo en MariaDB (no indexado aún)
        print("\nPaso 2: Crear un curso nuevo de prueba en MariaDB")
        title_new = "Curso de DevOps y Contenedores de Prueba"
        name_new = "curso-devops-contenedores-prueba"
        course = self.create_test_course(title_new, name_new, published=1)
        self.assertIsNotNone(course)
        print(f"  Curso creado: '{course.name}'")

        # Paso 3: Limpiar caché para forzar la ejecución de indexación
        print("\nPaso 3: Limpiar clave de caché de indexación en progreso")
        frappe.cache().delete_value("learning_search_indexing_in_progress")
        print("  Caché de indexación limpia")

        # Paso 4: Ejecutar la reconstrucción del índice (simulando la ejecución del hook after_migrate)
        print("\nPaso 4: Ejecutar reconstrucción del índice de búsqueda")
        from lms.sqlite import build_index
        build_index()
        print("  Índice reconstruido de forma síncrona")

        # Paso 5: Validar consistencia del índice SQLite con la base de datos MariaDB
        print("\nPaso 5: Verificar que el curso recién creado esté indexado (Consistencia)")
        from lms.sqlite import LearningSearch
        search = LearningSearch()

        # Buscar el curso recién creado
        res = search.search("DevOps y Contenedores")
        course_names = [r["name"] for r in res.get("results", []) if r["doctype"] == "LMS Course"]
        self.assertIn(
            course.name,
            course_names,
            f"Inconsistencia: El curso recién creado '{course.name}' no está presente en el índice de búsqueda"
        )
        print(f"  Confirmado: El curso de prueba '{course.name}' se encuentra indexado")

        # Verificar todos los cursos publicados en la BD para asegurar consistencia completa
        print("\nPaso 6: Verificar consistencia para todos los cursos publicados en MariaDB")
        published_courses = frappe.get_all("LMS Course", filters={"published": 1}, fields=["name", "title"])
        self.assertTrue(len(published_courses) > 0, "Debe haber al menos un curso publicado en MariaDB para validar")

        for db_course in published_courses:
            # Hacemos una búsqueda simple por el título del curso
            res_course = search.search(db_course.title)
            found_names = [r["name"] for r in res_course.get("results", []) if r["doctype"] == "LMS Course"]
            self.assertIn(
                db_course.name,
                found_names,
                f"Inconsistencia: El curso '{db_course.name}' con título '{db_course.title}' está publicado en MariaDB pero NO se encuentra en el índice de búsqueda SQLite"
            )
            print(f"  Curso '{db_course.name}' es consistente en el índice SQLite")

        print("\n" + "="*70)
        print("(n.n) INT-018: Prueba completada exitosamente")
        print("="*70)
