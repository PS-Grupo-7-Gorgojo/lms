import os
import unittest
from unittest.mock import patch

import frappe
from lms.lms.api import delete_batch
from lms.lms.test_helpers import BaseTestUtils


@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestBatchIntegration(BaseTestUtils):
	"""
	Clase para pruebas de integración de LMS Batch.
	Cubre el caso:
	- INT-020: Comportamiento al eliminar un lote (LMS Batch) con clases en vivo e inscripciones.
	"""

	def setUp(self):
		super().setUp()
		self.test_id = frappe.generate_hash()[:8]

		# Crear usuario Instructor
		self.instructor_email = f"instructor_{self.test_id}@example.com"
		self._create_user(
			email=self.instructor_email,
			first_name="Instructor",
			last_name="Test",
			roles=["Course Creator"]
		)

		# Crear curso
		self.course = self._create_course(
			title=f"Course for Batch Delete {self.test_id}", 
			instructor=self.instructor_email
		)

		# Crear lote
		self.batch = self._create_batch(
			course=self.course.name,
			instructor=self.instructor_email,
			title=f"Batch Delete {self.test_id}",
			evaluator=self.instructor_email
		)

		# Crear estudiante
		self.student_email = f"student_{self.test_id}@example.com"
		self._create_user(
			email=self.student_email,
			first_name="Student",
			last_name="Test",
			roles=["LMS Student"]
		)

		# Crear cuenta de zoom de prueba
		self.zoom_account_name = f"zoom_account_{self.test_id}"
		zoom_settings = frappe.get_doc({
			"doctype": "LMS Zoom Settings",
			"account_name": self.zoom_account_name,
			"member": self.instructor_email,
			"account_id": f"acc_{self.test_id}",
			"client_id": f"client_{self.test_id}",
			"client_secret": "test_client_secret",
			"enabled": 1
		})
		zoom_settings.insert(ignore_permissions=True)
		self.cleanup_items.append(("LMS Zoom Settings", zoom_settings.name))

	def test_delete_batch_integrity_checks(self):
		"""
		INT-020: Verificar que:
		1. La eliminación normal de un Batch mediante frappe.delete_doc sea prevenida
		   cuando existan clases en vivo (LMS Live Class) vinculadas (LinkExistsError).
		2. La llamada al endpoint delete_batch de la API elimine el lote por cascada 
		   a nivel de inscripciones pero deje huérfanas las clases en vivo (comportamiento actual).
		"""
		
		# Crear inscripción de estudiante en el lote
		batch_enrollment = self._create_batch_enrollment(self.student_email, self.batch.name)

		# Crear una clase en vivo asociada al lote
		# Mockeamos create_calendar_event para evitar dependencias con Google/Zoom APIs reales en el test
		with patch("lms.lms.doctype.lms_live_class.lms_live_class.LMSLiveClass.create_calendar_event") as mock_cal:
			live_class = frappe.get_doc({
				"doctype": "LMS Live Class",
				"title": f"Live Class {self.test_id}",
				"batch_name": self.batch.name,
				"date": frappe.utils.nowdate(),
				"time": "10:00:00",
				"duration": 60,
				"conferencing_provider": "Zoom",
				"zoom_account": self.zoom_account_name,
				"host": self.instructor_email,
				"timezone": "Asia/Kolkata"
			})
			live_class.insert(ignore_permissions=True)
			self.cleanup_items.append(("LMS Live Class", live_class.name))

		# Validar prevención: frappe.delete_doc de un Batch con clases asociadas debe lanzar LinkExistsError
		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc("LMS Batch", self.batch.name)

		# Cambiar sesión a un usuario con privilegios (Instructor) para probar el endpoint de API
		frappe.set_user(self.instructor_email)

		try:
			# Ejecutar la eliminación del lote vía API delete_batch
			delete_batch(self.batch.name)

			# Validar que el lote ya no existe
			self.assertFalse(frappe.db.exists("LMS Batch", self.batch.name))

			# Validar que la inscripción en el lote se borró en cascada por la API
			self.assertFalse(frappe.db.exists("LMS Batch Enrollment", batch_enrollment.name))

			# Validar que la clase en vivo aún existe (quedó huérfana, comportamiento actual de la API)
			self.assertTrue(frappe.db.exists("LMS Live Class", live_class.name))

		finally:
			# Restaurar usuario
			frappe.set_user("Administrator")
