# Copyright (c) 2022, Frappe and Contributors
# See license.txt

from unittest.mock import patch, MagicMock
import unittest

import frappe
from lms.lms.doctype.course_evaluator.course_evaluator import get_schedule_range_end_date


class TestCourseEvaluator(unittest.TestCase):
	# UT-CRS-EVAL-001
	def test_validate_unavailability_invalid_dates_throws(self):
		"""Si la fecha de inicio de indisponibilidad es mayor que la de fin, lanza ValidationError."""
		# Crear evaluador en memoria con fechas inválidas
		evaluator = frappe.get_doc({
			"doctype": "Course Evaluator",
			"evaluator": "teacher@example.com",
			"unavailable_from": "2026-07-25",
			"unavailable_to": "2026-07-20"
		})
		
		with self.assertRaises(frappe.ValidationError):
			evaluator.validate_unavailability()

	# UT-CRS-EVAL-002
	def test_validate_time_slots_invalid_time_throws(self):
		"""Si la hora de inicio es mayor o igual que la de fin en una agenda, lanza ValidationError."""
		# Crear evaluador en memoria con horario de inicio posterior al de fin
		evaluator = frappe.get_doc({
			"doctype": "Course Evaluator",
			"evaluator": "teacher@example.com",
			"schedule": [
				{"day": "Monday", "start_time": "14:00:00", "end_time": "12:00:00"}
			]
		})
		
		with self.assertRaises(frappe.ValidationError):
			evaluator.validate_time_slots()

	# UT-CRS-EVAL-003
	def test_validate_overlaps_throws(self):
		"""Si existen horarios superpuestos el mismo día para el mismo evaluador, lanza ValidationError."""
		# Crear evaluador con dos horarios superpuestos el lunes (10-12 y 11-13)
		evaluator = frappe.get_doc({
			"doctype": "Course Evaluator",
			"evaluator": "teacher@example.com",
			"schedule": [
				{"name": "slot-1", "day": "Monday", "start_time": "10:00:00", "end_time": "12:00:00"},
				{"name": "slot-2", "day": "Monday", "start_time": "11:00:00", "end_time": "13:00:00"}
			]
		})
		
		with self.assertRaises(frappe.ValidationError):
			evaluator.validate_time_slots()

	# UT-CRS-EVAL-004
	def test_validate_evaluator_role_assigns_role(self):
		"""Si el usuario evaluador no cuenta con el rol de Batch Evaluator, se le añade automáticamente."""
		evaluator = frappe.get_doc({
			"doctype": "Course Evaluator",
			"evaluator": "teacher@example.com"
		})
		
		# Simular rol ausente y mockear el documento de Usuario
		mock_user_doc = MagicMock()
		
		with patch("frappe.get_roles", return_value=["LMS Student"]), \
			 patch("frappe.get_doc", return_value=mock_user_doc):
			 
			evaluator.validate_evaluator_role()
			mock_user_doc.add_roles.assert_called_once_with("Batch Evaluator")

	# UT-CRS-EVAL-005
	def test_on_trash_removes_role(self):
		"""Al eliminar un Course Evaluator, se le remueve el rol Batch Evaluator de su registro de usuario."""
		evaluator = frappe.get_doc({
			"doctype": "Course Evaluator",
			"evaluator": "teacher@example.com"
		})
		
		mock_user_doc = MagicMock()
		
		# Simular rol presente y mockear remoción de rol
		with patch("frappe.get_roles", return_value=["LMS Student", "Batch Evaluator"]), \
			 patch("frappe.get_doc", return_value=mock_user_doc):
			 
			evaluator.on_trash()
			mock_user_doc.remove_roles.assert_called_once_with("Batch Evaluator")

	# UT-CRS-EVAL-006
	def test_get_schedule_range_end_date_with_earlier_batch(self):
		"""Si la fecha límite del lote es anterior al rango predeterminado (60 días), retorna la fecha del lote."""
		from frappe.utils import getdate
		start_date = "2026-07-20"
		# 60 días después de start_date es 2026-09-18. Lote termina el 2026-08-30 (antes).
		mock_batch_end_date = getdate("2026-08-30")
		
		with patch("frappe.db.get_value", return_value=mock_batch_end_date):
			result = get_schedule_range_end_date(start_date, batch="batch-1")
			self.assertEqual(result, mock_batch_end_date)

