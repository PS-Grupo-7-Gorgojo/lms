# Copyright (c) 2021, FOSS United and Contributors
# See license.txt

from unittest.mock import patch, MagicMock
from lms.lms.test_helpers import BaseTestUtils  

import frappe


class TestLMSEnrollment(BaseTestUtils):
	# UT-LMS-ENR-001
	def test_validate_duplicate_enrollment_throws(self):
		"""Si ya existe una inscripción para el mismo curso y miembro, lanza ValidationError."""
		# crea el documento
		enrollment = frappe.get_doc({
			"doctype": "LMS Enrollment",
			"course": "course-1",
			"member": "student@example.com",
			"name": "new_enrollment_name"
		})
		
		# verifica la comprobación de duplicados
		with patch("frappe.db.exists", return_value="existing_enrollment_name"):
			with self.assertRaises(frappe.ValidationError):
				enrollment.validate_duplicate_enrollment()

	# UT-LMS-ENR-002
	def test_disable_self_learning_non_admin_throws(self):
		"""Si el aprendizaje autodidacta está deshabilitado y el usuario no es administrador, lanza ValidationError."""
		# crea el documento
		enrollment = frappe.get_doc({
			"doctype": "LMS Enrollment",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# mockea detalles del curso y rol de usuario
		with patch("frappe.db.get_value") as mock_get_value, \
			 patch("lms.lms.doctype.lms_enrollment.lms_enrollment.is_admin", return_value=False):
			 
			mock_get_value.return_value = frappe._dict({
				"published": 1,
				"disable_self_learning": 1,
				"paid_course": 0,
				"paid_certificate": 0
			})
			
			with self.assertRaises(frappe.ValidationError):
				enrollment.validate_course_enrollment_eligibility()

	# UT-LMS-ENR-003
	def test_enrollment_from_batch_not_associated_throws(self):
		"""Si se intenta inscribir desde un lote que no está asociado con el curso, lanza ValidationError."""
		# crea el documento
		enrollment = frappe.get_doc({
			"doctype": "LMS Enrollment",
			"course": "course-1",
			"member": "student@example.com",
			"enrollment_from_batch": "batch-1"
		})
		
		# mockea curso normal y lote no asociado
		with patch("frappe.db.get_value") as mock_get_value, \
			 patch("frappe.db.exists", return_value=False):
			 
			mock_get_value.return_value = frappe._dict({
				"published": 1,
				"disable_self_learning": 0,
				"paid_course": 0,
				"paid_certificate": 0
			})
			
			with self.assertRaises(frappe.ValidationError):
				enrollment.validate_course_enrollment_eligibility()

	# UT-LMS-ENR-004
	def test_unpublished_course_non_admin_throws(self):
		"""Si el curso no está publicado y el usuario no es administrador, lanza ValidationError."""
		# crea el documento
		enrollment = frappe.get_doc({
			"doctype": "LMS Enrollment",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# mockea curso no publicado y no admin
		with patch("frappe.db.get_value") as mock_get_value, \
			 patch("lms.lms.doctype.lms_enrollment.lms_enrollment.is_admin", return_value=False):
			 
			mock_get_value.return_value = frappe._dict({
				"published": 0,
				"disable_self_learning": 0,
				"paid_course": 0,
				"paid_certificate": 0
			})
			
			with self.assertRaises(frappe.ValidationError):
				enrollment.validate_course_enrollment_eligibility()

	# UT-LMS-ENR-005
	def test_paid_course_non_admin_no_payment_throws(self):
		"""Si el curso es de pago, el usuario no es administrador y no ha realizado el pago, lanza ValidationError."""
		# crea el documento
		enrollment = frappe.get_doc({
			"doctype": "LMS Enrollment",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# mockea detalles del curso, rol e inexistencia de pago
		with patch("frappe.db.get_value") as mock_get_value, \
			 patch("lms.lms.doctype.lms_enrollment.lms_enrollment.is_admin", return_value=False), \
			 patch("frappe.db.exists", return_value=False):
			 
			mock_get_value.return_value = frappe._dict({
				"published": 1,
				"disable_self_learning": 0,
				"paid_course": 1,
				"paid_certificate": 0
			})
			
			with self.assertRaises(frappe.ValidationError):
				enrollment.validate_course_enrollment_eligibility()

	# UT-LMS-ENR-006
	def test_paid_course_non_admin_payment_exists_passes(self):
		"""Si el curso es de pago, el usuario no es administrador y ya ha realizado el pago, permite la inscripción."""
		# crea el documento
		enrollment = frappe.get_doc({
			"doctype": "LMS Enrollment",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# mockea detalles del curso, rol y existencia de pago exitoso
		with patch("frappe.db.get_value") as mock_get_value, \
			 patch("lms.lms.doctype.lms_enrollment.lms_enrollment.is_admin", return_value=False), \
			 patch("frappe.db.exists", return_value="PAY-0001"):
			 
			mock_get_value.return_value = frappe._dict({
				"published": 1,
				"disable_self_learning": 0,
				"paid_course": 1,
				"paid_certificate": 0
			})
			
			# Debería ejecutarse sin lanzar ningún error
			enrollment.validate_course_enrollment_eligibility()

	# UT-LMS-ENR-007
	def test_update_program_progress(self):
		"""Verifica que update_program_progress calcule correctamente el progreso redondeando hacia arriba y actualice el valor."""
		from lms.lms.doctype.lms_enrollment.lms_enrollment import update_program_progress
		
		# Simular get_all para retornar el miembro del programa y luego la lista de cursos
		mock_get_all = MagicMock()
		mock_get_all.side_effect = [
			[frappe._dict({"parent": "Program-1", "name": "MEMBER-001"})],
			["Course-1", "Course-2"]
		]
		
		# Simular db.get_value para retornar progresos (Suma = 50 + 101 = 151. Promedio = 75.5 -> ceil = 76)
		mock_db_get_value = MagicMock()
		mock_db_get_value.side_effect = [50, 101]
		
		mock_db_set_value = MagicMock()
		
		with patch("frappe.get_all", mock_get_all), \
			 patch("frappe.db.get_value", mock_db_get_value), \
			 patch("frappe.db.set_value", mock_db_set_value):
			 
			update_program_progress("student@example.com")
			
		mock_db_set_value.assert_called_once_with("LMS Program Member", "MEMBER-001", "progress", 76)
