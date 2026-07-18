"""
Pruebas de integración para Módulo 2: Permisos y Roles
Casos: INT-021 (Course Creator puede matricularse en su propio curso)
       INT-022 (Moderator no puede ver submission de otro batch)
"""
import os
import unittest

import frappe
from lms.lms.test_helpers import BaseTestUtils


@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestPermissionsIntegration(BaseTestUtils):
	"""
	Clase para pruebas de integración de permisos en el LMS de Frappe.
	Cubre los casos:
	- INT-021: El Course Creator se puede matricular en su propio curso.
	- INT-022: Un Moderador no puede acceder a las entregas de cuestionarios (Quiz Submissions)
	  de estudiantes de otros lotes (o que no le pertenecen).
	"""

	def setUp(self):
		super().setUp()

	def test_course_creator_can_enroll_in_own_course(self):
		"""
		INT-021: Validar que un usuario con rol 'Course Creator' pueda
		matricularse de manera normal en su propio curso.
		"""
		test_id = frappe.generate_hash()[:8]
		creator_email = f"creator_{test_id}@example.com"

		# Crear el usuario Course Creator
		self._create_user(
			email=creator_email,
			first_name="Course",
			last_name="Creator",
			roles=["Course Creator"]
		)

		# Crear un curso donde este usuario es el instructor
		course = self._create_course(
			title=f"Course for Instructor {test_id}",
			instructor=creator_email
		)

		# Cambiar la sesión activa al usuario Course Creator
		frappe.set_user(creator_email)

		try:
			# Intentar matricularse en el curso
			enrollment = frappe.new_doc("LMS Enrollment")
			enrollment.update({
				"course": course.name,
				"member": creator_email
			})
			enrollment.insert(ignore_permissions=False)

			# Guardar para cleanup y verificar que se insertó correctamente
			self.cleanup_items.append(("LMS Enrollment", enrollment.name))
			self.assertTrue(frappe.db.exists("LMS Enrollment", enrollment.name))
			self.assertEqual(enrollment.member, creator_email)
			self.assertEqual(enrollment.course, course.name)

		finally:
			# Restaurar el usuario activo a Administrator
			frappe.set_user("Administrator")

	def test_moderator_cannot_view_quiz_submission_from_other_batch(self):
		"""
		INT-022: Validar que un Moderador no pueda visualizar los registros de
		entregas de cuestionarios ('LMS Quiz Submission') de estudiantes de otros lotes.
		"""
		test_id = frappe.generate_hash()[:8]
		student_email = f"student_{test_id}@example.com"
		moderator_email = f"moderator_{test_id}@example.com"

		# Crear estudiante de prueba
		self._create_user(
			email=student_email,
			first_name="Student",
			last_name="Test",
			roles=["LMS Student"]
		)

		# Crear curso de prueba
		course = self._create_course(title=f"Utility Course {test_id}")

		# Crear cuestionario (LMS Quiz) de prueba
		quiz = frappe.get_doc({
			"doctype": "LMS Quiz",
			"title": f"Utility Quiz {test_id}",
			"passing_percentage": 70,
			"total_marks": 15
		})
		quiz.insert(ignore_permissions=True)
		self.cleanup_items.append(("LMS Quiz", quiz.name))

		# Crear un registro de entrega de cuestionario (LMS Quiz Submission) para el estudiante
		submission = frappe.get_doc({
			"doctype": "LMS Quiz Submission",
			"quiz": quiz.name,
			"member": student_email,
			"score": 12,
			"score_out_of": 15,
			"percentage": 80,
			"passing_percentage": 70
		})
		# Establecer explícitamente el owner para simular que pertenece al estudiante
		submission.owner = student_email
		submission.insert(ignore_permissions=True)
		self.cleanup_items.append(("LMS Quiz Submission", submission.name))

		# Crear un Moderador de prueba
		self._create_user(
			email=moderator_email,
			first_name="Test",
			last_name="Moderator",
			roles=["Moderator"]
		)

		# Cambiar la sesión activa al Moderador de prueba
		frappe.set_user(moderator_email)

		try:
			# Intentar acceder y verificar permisos sobre la entrega del estudiante
			# Esto debe lanzar una excepción de permisos (PermissionError) ya que no le pertenece
			with self.assertRaises(frappe.PermissionError):
				doc = frappe.get_doc("LMS Quiz Submission", submission.name)
				doc.check_permission("read")

		finally:
			# Restaurar el usuario activo a Administrator
			frappe.set_user("Administrator")
