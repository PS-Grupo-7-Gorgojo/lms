# Copyright (c) 2021, FOSS United and Contributors
# See license.txt

from unittest.mock import patch, MagicMock
import unittest

import frappe


class TestLMSCertificate(unittest.TestCase):
	# UT-LMS-CERT-001
	def test_validate_no_course_no_batch_non_admin_throws(self):
		"""Si no se especifica curso ni lote y el usuario no tiene rol administrativo, lanza ValidationError."""
		# Crear el certificado sin curso ni lote
		certificate = frappe.get_doc({
			"doctype": "LMS Certificate",
			"member": "student@example.com"
		})
		
		# Parchear roles para no administrador
		with patch("frappe.get_roles", return_value=["LMS Student"]):
			with self.assertRaises(frappe.ValidationError):
				certificate.validate_role_of_owner()

	# UT-LMS-CERT-002
	def test_validate_course_not_enrolled_throws(self):
		"""Si el miembro no está inscrito en el curso para el que se emite el certificado, lanza ValidationError."""
		# Crear el certificado
		certificate = frappe.get_doc({
			"doctype": "LMS Certificate",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# Parchear inexistencia de inscripción en la base de datos
		with patch("frappe.db.exists", return_value=False):
			with self.assertRaises(frappe.ValidationError):
				certificate.validate_course_enrollment()

	# UT-LMS-CERT-003
	def test_validate_course_incomplete_throws(self):
		"""Si la certificación está habilitada pero el miembro no ha alcanzado el 100% de progreso, lanza ValidationError."""
		# Crear el certificado
		certificate = frappe.get_doc({
			"doctype": "LMS Certificate",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# Parchear inscripción existente, certificación del curso habilitada y progreso del estudiante al 85%
		with patch("frappe.db.exists", return_value=True), \
			 patch("frappe.db.get_value") as mock_get_value:
			 
			mock_get_value.side_effect = lambda dt, filters, fieldname=None: (
				1 if dt == "LMS Course" else 85
			)
			
			with self.assertRaises(frappe.ValidationError):
				certificate.validate_course_enrollment()

	# UT-LMS-CERT-004
	def test_validate_course_duplicate_throws(self):
		"""Si el miembro ya posee un certificado para el mismo curso, lanza ValidationError."""
		# Crear el certificado
		certificate = frappe.get_doc({
			"doctype": "LMS Certificate",
			"course": "course-1",
			"member": "student@example.com",
			"name": "new_cert"
		})
		
		# Simular certificado duplicado encontrado y recuperar el nombre del usuario
		mock_duplicates = [frappe._dict({"name": "existing_cert", "course_title": "Course Title"})]
		
		with patch("frappe.get_all", return_value=mock_duplicates), \
			 patch("frappe.db.get_value", return_value="Student Name"):
			 
			with self.assertRaises(frappe.ValidationError):
				certificate.validate_course_duplicates()

	# UT-LMS-CERT-005
	def test_validate_certification_eligibility_not_enabled_throws(self):
		"""Si la certificación no está habilitada para el curso, lanza ValidationError al intentar validar la elegibilidad."""
		from lms.lms.doctype.lms_certificate.lms_certificate import validate_certification_eligibility
		
		# Simular inscripción existente pero certificación deshabilitada en el curso
		with patch("frappe.db.exists", return_value=True), \
			 patch("frappe.db.get_value", return_value=0):
			 
			with self.assertRaises(frappe.ValidationError):
				validate_certification_eligibility("course-1")

	# UT-LMS-CERT-006
	def test_has_permission_denied_for_unpublished(self):
		"""Si el usuario no es admin ni el propietario del documento, y el certificado no está publicado, se deniega el acceso."""
		from lms.lms.doctype.lms_certificate.lms_certificate import has_permission
		
		# Crear el certificado no publicado propiedad de otro usuario
		certificate = frappe.get_doc({
			"doctype": "LMS Certificate",
			"owner": "student@example.com",
			"published": 0
		})
		
		# Simular roles de usuario estudiante sin permisos administrativos
		with patch("frappe.get_roles", return_value=["LMS Student"]):
			result = has_permission(certificate, ptype="read", user="stranger@example.com")
			self.assertFalse(result)
