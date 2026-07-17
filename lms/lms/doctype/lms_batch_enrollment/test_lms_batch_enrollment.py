# Copyright (c) 2025, Frappe and Contributors
# See license.txt

from unittest.mock import patch, MagicMock
from frappe.tests import UnitTestCase

import frappe
from lms.lms.doctype.lms_batch_enrollment.lms_batch_enrollment import send_confirmation_email


class UnitTestLMSBatchEnrollment(UnitTestCase):
	# UT-LMS-BATCHENR-001
	def test_validate_owner_different_non_admin_throws(self):
		"""Si el propietario es diferente del miembro y no es administrador, lanza ValidationError."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"owner": "evaluator@example.com",
			"member": "student@example.com"
		})
		
		# Simular rol ordinario del usuario
		with patch("frappe.get_roles", return_value=["LMS Student"]):
			with self.assertRaises(frappe.ValidationError):
				batch_enrollment.validate_owner()

	# UT-LMS-BATCHENR-002
	def test_paid_batch_no_payment_throws(self):
		"""Si el lote es de pago, el usuario no es admin y no ha pagado, lanza ValidationError."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"batch": "batch-1",
			"member": "student@example.com"
		})
		
		# Parchear lote de pago, usuario no admin e inexistencia de pago
		with patch("frappe.db.get_value", return_value=1), \
			 patch.object(batch_enrollment, "is_admin", return_value=False), \
			 patch("frappe.db.exists", return_value=False):
			 
			with self.assertRaises(frappe.ValidationError):
				batch_enrollment.validate_payment()

	# UT-LMS-BATCHENR-003
	def test_paid_batch_payment_exists_passes(self):
		"""Si el lote es de pago, el usuario no es admin y ya pagó, permite la inscripción y guarda el pago."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"batch": "batch-1",
			"member": "student@example.com"
		})
		
		# Parchear lote de pago, usuario no admin y pago registrado
		with patch("frappe.db.get_value", return_value=1), \
			 patch.object(batch_enrollment, "is_admin", return_value=False), \
			 patch("frappe.db.exists", return_value="PAY-0002"):
			 
			batch_enrollment.validate_payment()
			self.assertEqual(batch_enrollment.payment, "PAY-0002")

	# UT-LMS-BATCHENR-004
	def test_validate_self_enrollment_restricted_non_admin_throws(self):
		"""Si la autoinscripción está deshabilitada y el usuario no es admin, lanza ValidationError."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"batch": "batch-1",
			"member": "student@example.com"
		})
		
		# Parchear autoinscripción deshabilitada y usuario no admin
		with patch("frappe.db.get_value", return_value=frappe._dict({"allow_self_enrollment": 0, "paid_batch": 0})), \
			 patch.object(batch_enrollment, "is_admin", return_value=False):
			 
			with self.assertRaises(frappe.ValidationError):
				batch_enrollment.validate_self_enrollment()

	# UT-LMS-BATCHENR-005
	def test_validate_duplicate_members_throws(self):
		"""Si el miembro ya está inscrito en el lote, lanza ValidationError."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"batch": "batch-1",
			"member": "student@example.com",
			"name": "new_batch_enr"
		})
		
		# Simular duplicado existente
		with patch("frappe.db.exists", return_value="existing_batch_enr"):
			with self.assertRaises(frappe.ValidationError):
				batch_enrollment.validate_duplicate_members()

	# UT-LMS-BATCHENR-006
	def test_validate_seat_availability_exceeded_throws(self):
		"""Si la cantidad de inscritos alcanza o supera el número de vacantes, lanza ValidationError."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"batch": "batch-1",
			"member": "student@example.com"
		})
		
		# Parchear vacantes al límite e inscritos llenos
		with patch("frappe.db.get_value", return_value=10), \
			 patch("frappe.db.count", return_value=10):
			 
			with self.assertRaises(frappe.ValidationError):
				batch_enrollment.validate_seat_availability()

	# UT-LMS-BATCHENR-007
	def test_validate_course_enrollment_creates_missing_enrollment(self):
		"""Si el estudiante no está inscrito en los cursos del lote, crea las inscripciones automáticamente."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"batch": "batch-1",
			"member": "student@example.com"
		})
		
		mock_courses = [frappe._dict({"course": "course-1"})]
		mock_enrollment = MagicMock()
		
		# Simular cursos asociados y nueva inscripción
		with patch("frappe.get_all", return_value=mock_courses), \
			 patch("frappe.db.exists", return_value=False), \
			 patch("frappe.new_doc", return_value=mock_enrollment):
			 
			batch_enrollment.validate_course_enrollment()
			
			# Verificar asignaciones y almacenamiento
			self.assertEqual(mock_enrollment.course, "course-1")
			self.assertEqual(mock_enrollment.member, "student@example.com")
			self.assertEqual(mock_enrollment.enrollment_from_batch, "batch-1")
			mock_enrollment.save.assert_called_once()

	# UT-LMS-BATCHENR-008
	def test_send_confirmation_email_no_permission_throws(self):
		"""Si el remitente no es el miembro inscrito ni administrador, lanza PermissionError."""
		# Crear el documento
		batch_enrollment = frappe.get_doc({
			"doctype": "LMS Batch Enrollment",
			"batch": "batch-1",
			"member": "student@example.com"
		})
		
		# Parchear rol de usuario (no admin) y usuario de sesión diferente al miembro
		with patch("frappe.get_roles", return_value=["LMS Student"]):
			original_user = frappe.session.user
			frappe.session.user = "stranger@example.com"
			try:
				with self.assertRaises(frappe.PermissionError):
					send_confirmation_email(batch_enrollment)
			finally:
				frappe.session.user = original_user
