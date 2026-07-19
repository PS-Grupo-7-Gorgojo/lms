import os
import unittest
import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import get_quiz_with_questions

@unittest.skipUnless(os.environ.get("RUN_SECURITY_TESTS"), "Skipping security tests")
class TestSecuritySECLMS001(BaseTestUtils):
	def setUp(self):
		super().setUp()

	def test_sec_lms_001_student_cannot_access_unenrolled_quiz(self):
		"""
		SEC-LMS-001: IDOR en el Acceso a Preguntas de Cuestionarios.
		Un estudiante con rol 'LMS Student' no debe poder acceder a las preguntas
		y explicaciones de un cuestionario (LMS Quiz) de un curso en el cual no está inscrito.
		"""
		test_id = frappe.generate_hash()[:8]
		student_email = f"student_sec_{test_id}@example.com"
		creator_email = f"creator_sec_{test_id}@example.com"

		self._create_user(
			email=student_email,
			first_name="LMS",
			last_name="Student",
			roles=["LMS Student"]
		)

		course = self._create_course(
			title=f"Private Security Course {test_id}",
			instructor=creator_email
		)

		self.questions = self._create_quiz_questions()

		quiz = frappe.new_doc("LMS Quiz")
		quiz.update({
			"title": f"Security Quiz {test_id}",
			"course": course.name,
			"passing_percentage": 70,
			"total_marks": 15,
		})
		for question in self.questions:
			quiz.append("questions", {"question": question.name, "marks": 5})
		quiz.insert(ignore_permissions=True)
		self.cleanup_items.append(("LMS Quiz", quiz.name))

		frappe.set_user(student_email)

		try:
			with self.assertRaises(frappe.PermissionError):
				get_quiz_with_questions(quiz.name)
		finally:
			frappe.set_user("Administrator")
