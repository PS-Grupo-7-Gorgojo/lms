"""
Pruebas de integración para Módulo 2: Usuarios
Casos: INT-001 (Crear usuario → se le asigna rol LMS Student automáticamente)
"""
import os
import unittest

import frappe
from lms.lms.test_helpers import BaseTestUtils


@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestUserIntegration(BaseTestUtils):
	"""
	Clase para probar comportamientos y hooks relacionados con la creación y roles del usuario.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_int_001_automatic_role_assignment(self):
		"""
		INT-001: Crear usuario → se le asigna rol LMS Student automáticamente.
		Verifica que al insertar un nuevo usuario, se asigne automáticamente
		el rol de 'LMS Student' a través del hook before_insert.
		"""
		test_id = frappe.generate_hash()[:8]
		email = f"student_{test_id}@example.com"

		# Crear usuario básico sin asignar roles manualmente
		user = frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": "Test",
			"last_name": f"Student {test_id}",
			"send_welcome_email": 0
		})
		user.insert(ignore_permissions=True)
		self.cleanup_items.append(("User", user.name))

		# Recargar el documento para verificar los datos guardados en la BD
		user.reload()

		# Verificar que el rol "LMS Student" está asignado
		has_student_role = any(r.role == "LMS Student" for r in user.roles)
		self.assertTrue(has_student_role, "The user should automatically be assigned the LMS Student role.")
