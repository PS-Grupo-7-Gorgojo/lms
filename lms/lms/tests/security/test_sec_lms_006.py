import os
import unittest
import frappe
from lms.lms.test_helpers import BaseTestUtils

@unittest.skipUnless(os.environ.get("RUN_SECURITY_TESTS"), "Skipping security tests")
class TestSecuritySECLMS006(BaseTestUtils):
	def setUp(self):
		super().setUp()

	def test_sec_lms_006_cannot_steal_private_attachments(self):
		"""
		SEC-LMS-006: Asociación Ilícita de Archivos Privados en Tareas (IDOR).
		Un estudiante no debe poder adjuntar un archivo privado perteneciente a otro
		usuario a su propia entrega de tareas (LMS Assignment Submission) y así ganar acceso a él.
		"""
		test_id = frappe.generate_hash()[:8]
		victim_email = f"victim_sec6_{test_id}@example.com"
		attacker_email = f"attacker_sec6_{test_id}@example.com"

		# 1. Crear usuario víctima (propietario del archivo) y usuario atacante (estudiante)
		self._create_user(
			email=victim_email,
			first_name="Victim",
			last_name="User",
			roles=["LMS Student"]
		)
		self._create_user(
			email=attacker_email,
			first_name="Attacker",
			last_name="Student",
			roles=["LMS Student"]
		)

		# 2. Crear una tarea
		assignment = self._create_assignment(f"Assignment SEC6 {test_id}")

		# 3. Crear un archivo privado con el propietario establecido en la víctima
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": f"confidential_doc_{test_id}.png",
			"content": b"Private picture content.",
			"is_private": 1
		})
		file_doc.owner = victim_email
		file_doc.insert(ignore_permissions=True)
		self.cleanup_items.append(("File", file_doc.name))

		# 4. Cambiar sesión al usuario atacante
		frappe.set_user(attacker_email)

		try:
			# 5. Intentar crear una entrega de tarea con HTML que hace referencia al archivo privado de la víctima
			submission = frappe.new_doc("LMS Assignment Submission")
			submission.update({
				"assignment": assignment.name,
				"member": attacker_email,
				"type": "Text",
				"answer": f'<p>Here is my task: <img src="{file_doc.file_url}" /></p>'
			})

			# El sistema debería lanzar una excepción (ValidationError o PermissionError) al intentar salvar o actualizar
			with self.assertRaises(frappe.PermissionError):
				submission.insert(ignore_permissions=False)
		finally:
			# Restaurar usuario
			frappe.set_user("Administrator")
