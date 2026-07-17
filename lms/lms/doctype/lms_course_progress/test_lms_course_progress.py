# Copyright (c) 2021, FOSS United and Contributors
# See license.txt

from unittest.mock import patch
import unittest

import frappe


class TestLMSCourseProgress(unittest.TestCase):
	# UT-LMS-CRSPROG-001
	def test_before_insert_duplicate_progress_throws(self):
		"""Si ya existe un registro de progreso para la misma lección y miembro, lanza UniqueValidationError."""
		progress = frappe.get_doc({
			"doctype": "LMS Course Progress",
			"member": "student@example.com",
			"lesson": "lesson-1"
		})
		
		# Parchear la existencia del progreso duplicado
		with patch("frappe.db.exists", return_value=True):
			with self.assertRaises(frappe.UniqueValidationError):
				progress.before_insert()

	# UT-LMS-CRSPROG-002
	def test_on_update_recalculates_progress(self):
		"""Al actualizar el progreso, invoca a recalculate_course_progress para actualizar la inscripción."""
		progress = frappe.get_doc({
			"doctype": "LMS Course Progress",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# Parchear el recálculo de avance
		with patch("lms.lms.doctype.lms_course_progress.lms_course_progress.recalculate_course_progress") as mock_recalc:
			progress.on_update()
			mock_recalc.assert_called_once_with("course-1", "student@example.com")

	# UT-LMS-CRSPROG-003
	def test_after_delete_recalculates_progress(self):
		"""Al eliminar el progreso, invoca a recalculate_course_progress para actualizar la inscripción."""
		progress = frappe.get_doc({
			"doctype": "LMS Course Progress",
			"course": "course-1",
			"member": "student@example.com"
		})
		
		# Parchear el recálculo de avance
		with patch("lms.lms.doctype.lms_course_progress.lms_course_progress.recalculate_course_progress") as mock_recalc:
			progress.after_delete()
			mock_recalc.assert_called_once_with("course-1", "student@example.com")
