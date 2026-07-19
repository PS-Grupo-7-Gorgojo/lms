import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz
import json

class TestSecuritySECLMS002(BaseTestUtils):
	def setUp(self):
		super().setUp()

	def test_sec_lms_002_stored_xss_in_quiz_is_prevented(self):
		"""
		SEC-LMS-002: Stored XSS mediante Conversor de Base64 en Quiz.
		Verificar que no se puedan inyectar archivos HTML o SVG maliciosos camuflados
		como imágenes Base64 en las respuestas de preguntas "Open Ended".
		"""
		# 1. Generar ID único y crear usuario estudiante
		test_id = frappe.generate_hash()[:8]
		student_email = f"student_sec2_{test_id}@example.com"
		self._create_user(
			email=student_email,
			first_name="LMS",
			last_name="Student",
			roles=["LMS Student"]
		)

		# 2. Crear una pregunta de tipo "Open Ended"
		question = frappe.new_doc("LMS Question")
		question.update({
			"question": f"Open Ended Question {test_id}?",
			"type": "Open Ended",
		})
		question.save(ignore_permissions=True)
		self.cleanup_items.append(("LMS Question", question.name))

		# 3. Crear un cuestionario (LMS Quiz) y añadir la pregunta
		quiz = frappe.new_doc("LMS Quiz")
		quiz.update({
			"title": f"Security Quiz 2 {test_id}",
			"passing_percentage": 50,
			"total_marks": 5,
		})
		quiz.append("questions", {"question": question.name, "marks": 5})
		quiz.save(ignore_permissions=True)
		self.cleanup_items.append(("LMS Quiz", quiz.name))

		# 4. Cambiar sesión al estudiante
		frappe.set_user(student_email)

		# 5. Payload malicioso: un archivo HTML/JS camuflado como base64 en una etiqueta img
		payload_results = [
			{
				"question_name": question.name,
				"answer": ["<img src=\"data:text/html;filename=exploit.html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=\" />"]
			}
		]

		try:
			# 6. Intentar enviar el quiz
			# El sistema debe rechazar la creación del archivo no seguro (ValidationError)
			with self.assertRaises(frappe.ValidationError):
				submit_quiz(quiz.name, json.dumps(payload_results))
		finally:
			# Restaurar usuario
			frappe.set_user("Administrator")
