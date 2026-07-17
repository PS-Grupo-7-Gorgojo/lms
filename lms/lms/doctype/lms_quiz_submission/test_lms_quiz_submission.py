# Copyright (c) 2021, FOSS United and Contributors
# See license.txt

from unittest.mock import patch, MagicMock
import unittest

import frappe


class TestLMSQuizSubmission(unittest.TestCase):
	# UT-LMS-QUIZSUB-001
	def test_validate_if_max_attempts_exceeded_throws(self):
		"""Si la cantidad de intentos realizados supera el límite de intentos permitidos, lanza MaximumAttemptsExceededError."""
		# Crear el documento en memoria
		submission = frappe.get_doc({
			"doctype": "LMS Quiz Submission",
			"quiz": "quiz-1",
			"member": "student@example.com"
		})
		
		from lms.lms.doctype.lms_quiz_submission.lms_quiz_submission import MaximumAttemptsExceededError
		
		# Parchear intentos máximos (3) y cantidad de intentos del usuario (3)
		with patch("frappe.db.get_value", return_value=3), \
			 patch("frappe.db.count", return_value=3):
			 
			with self.assertRaises(MaximumAttemptsExceededError):
				submission.validate_if_max_attempts_exceeded()

	# UT-LMS-QUIZSUB-002
	def test_validate_marks_greater_than_out_of_throws(self):
		"""Si la nota asignada a una pregunta es mayor que el puntaje máximo permitido para ella, lanza ValidationError."""
		# Crear el documento en memoria con un resultado inválido (5 sobre 4)
		submission = frappe.get_doc({
			"doctype": "LMS Quiz Submission",
			"quiz": "quiz-1",
			"member": "student@example.com",
			"result": [
				frappe._dict({"idx": 1, "marks": 5, "marks_out_of": 4})
			]
		})
		
		with self.assertRaises(frappe.ValidationError):
			submission.validate_marks()

	# UT-LMS-QUIZSUB-003
	def test_set_percentage_calculates_correctly(self):
		"""Calcula correctamente el porcentaje basándose en la nota obtenida (score) y la nota máxima (score_out_of)."""
		# Crear el documento en memoria
		submission = frappe.get_doc({
			"doctype": "LMS Quiz Submission",
			"quiz": "quiz-1",
			"member": "student@example.com",
			"score": 15,
			"score_out_of": 20
		})
		
		# Calcular el porcentaje (15 / 20 * 100 = 75%)
		submission.set_percentage()
		self.assertEqual(submission.percentage, 75.0)

	# UT-LMS-QUIZSUB-004
	def test_notify_member_on_score_change(self):
		"""Envía una notificación si la calificación del alumno cambia y no es cero."""
		# Crear el documento en memoria
		submission = frappe.get_doc({
			"doctype": "LMS Quiz Submission",
			"name": "SUB-001",
			"quiz": "quiz-1",
			"quiz_title": "Quiz Title",
			"member": "student@example.com",
			"score": 18
		})
		
		# Parchear has_value_changed (True) y la creación de la notificación
		with patch.object(submission, "has_value_changed", return_value=True), \
			 patch("lms.lms.doctype.lms_quiz_submission.lms_quiz_submission.make_notification_logs") as mock_notify:
			 
			original_user = frappe.session.user
			frappe.session.user = "evaluator@example.com"
			try:
				submission.notify_member()
				
				# Comprobar que se llamó al creador de notificaciones de Frappe
				mock_notify.assert_called_once()
				notification_arg = mock_notify.call_args[0][0]
				self.assertEqual(notification_arg["for_user"], "student@example.com")
				self.assertEqual(notification_arg["from_user"], "evaluator@example.com")
			finally:
				frappe.session.user = original_user
