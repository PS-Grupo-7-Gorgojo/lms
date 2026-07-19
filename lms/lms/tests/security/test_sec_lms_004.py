import os
import unittest
import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import validate_image

@unittest.skipUnless(os.environ.get("RUN_SECURITY_TESTS"), "Skipping security tests")
class TestSecuritySECLMS004(BaseTestUtils):
	def setUp(self):
		super().setUp()

	def test_sec_lms_004_unauthorized_user_cannot_leak_private_file(self):
		"""
		SEC-LMS-004: Fuga de Archivos Privados mediante Imagen de Curso (IDOR).
		Un Course Creator no debe poder usar `validate_image` sobre un archivo privado
		perteneciente a otro usuario para hacerlo público.
		"""
		test_id = frappe.generate_hash()[:8]
		victim_email = f"victim_sec4_{test_id}@example.com"
		attacker_email = f"attacker_sec4_{test_id}@example.com"

		# 1. Crear usuario víctima (propietario del archivo privado) y usuario atacante (Course Creator)
		self._create_user(
			email=victim_email,
			first_name="Victim",
			last_name="User",
			roles=["LMS Student"]
		)
		self._create_user(
			email=attacker_email,
			first_name="Attacker",
			last_name="Creator",
			roles=["Course Creator"]
		)

		# 2. Crear un archivo privado con el propietario establecido en la víctima
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": f"confidential_doc_{test_id}.txt",
			"content": b"Confidential financial details.",
			"is_private": 1
		})
		file_doc.owner = victim_email
		file_doc.insert(ignore_permissions=True)
		self.cleanup_items.append(("File", file_doc.name))

		# 3. Cambiar sesión al usuario atacante
		frappe.set_user(attacker_email)

		try:
			# 4. Intentar ejecutar validate_image sobre el archivo privado de la víctima
			# El sistema debería lanzar una excepción de permisos (PermissionError)
			with self.assertRaises(frappe.PermissionError):
				validate_image(file_doc.file_url)
		finally:
			# Restaurar usuario
			frappe.set_user("Administrator")
