# Copyright (c) 2023, Frappe and Contributors
# See license.txt

from unittest.mock import patch, MagicMock
from frappe.tests import UnitTestCase

import frappe


class TestLMSQuestion(UnitTestCase):
	# UT-LMS-QUEST-001
	def test_validate_duplicate_options_throws(self):
		"""Si hay opciones duplicadas en una pregunta de opción múltiple, lanza ValidationError."""
		question = frappe.get_doc({
			"doctype": "LMS Question",
			"type": "Choices",
			"option_1": "Same Option",
			"option_2": "Same Option",
			"option_3": "Other Option",
			"is_correct_1": 1
		})
		
		with self.assertRaises(frappe.ValidationError):
			question.validate()

	# UT-LMS-QUEST-002
	def test_validate_minimum_options_throws(self):
		"""Si falta la opción 1 o la opción 2 en una pregunta de opción múltiple, lanza ValidationError."""
		question = frappe.get_doc({
			"doctype": "LMS Question",
			"type": "Choices",
			"option_1": "Only Option",
			"option_2": "",
			"is_correct_1": 1
		})
		
		with self.assertRaises(frappe.ValidationError):
			question.validate()

	# UT-LMS-QUEST-003
	def test_validate_correct_options_none_throws(self):
		"""Si no hay al menos una opción marcada como correcta en una pregunta de opción múltiple, lanza ValidationError."""
		question = frappe.get_doc({
			"doctype": "LMS Question",
			"type": "Choices",
			"option_1": "Option A",
			"option_2": "Option B",
			"is_correct_1": 0,
			"is_correct_2": 0
		})
		
		with self.assertRaises(frappe.ValidationError):
			question.validate()

	# UT-LMS-QUEST-004
	def test_validate_possible_answer_none_throws(self):
		"""Si la pregunta es de entrada de texto libre y no tiene respuestas posibles asignadas, lanza ValidationError."""
		question = frappe.get_doc({
			"doctype": "LMS Question",
			"type": "User Input",
			"question": "What is the capital of France?",
			"possibility_1": "",
			"possibility_2": ""
		})
		
		with self.assertRaises(frappe.ValidationError):
			question.validate()

	# UT-LMS-QUEST-005
	def test_update_question_title_updates_referenced_rows(self):
		"""Si la pregunta no es nueva y se actualiza su título, debe modificar el detalle en todas las filas de cuestionarios correspondientes."""
		question = frappe.get_doc({
			"doctype": "LMS Question",
			"name": "Q-001",
			"type": "Choices",
			"question": "Old Question Title",
			"option_1": "Option A",
			"option_2": "Option B",
			"is_correct_1": 1
		})
		
		# Simular que el documento no es nuevo
		question.is_new = MagicMock(return_value=False)
		question.question = "New Question Title"
		
		# Parchear consultas y set_value de la base de datos
		mock_quiz_questions = ["Row-1", "Row-2"]
		mock_db_set_value = MagicMock()
		
		with patch("frappe.get_all", return_value=mock_quiz_questions), \
			 patch("frappe.db.set_value", mock_db_set_value):
			 
			question.validate()
			
			# Comprobar que se llamó a set_value para actualizar el título referenciado
			self.assertEqual(mock_db_set_value.call_count, 2)
			mock_db_set_value.assert_any_call("LMS Quiz Question", "Row-1", "question_detail", "New Question Title")
			mock_db_set_value.assert_any_call("LMS Quiz Question", "Row-2", "question_detail", "New Question Title")
