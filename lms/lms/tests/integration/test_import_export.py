import glob
import os
import re
import unittest
import zipfile

import frappe
from lms.lms.api import export_course_as_zip, import_course_from_zip
from lms.lms.test_helpers import BaseTestUtils


@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestImportExportIntegration(BaseTestUtils):
	"""
	Clase para pruebas de integración de Importación y Exportación de Cursos.
	Cubre los casos:
	- INT-015: Exportación de curso y evaluaciones a ZIP.
	- INT-016: Importación de curso desde ZIP.
	"""

	def setUp(self):
		super().setUp()
		self._setup_unique_course_flow()

	def _setup_unique_course_flow(self):
		self.test_id = frappe.generate_hash()[:8]
		
		# Crear usuarios de prueba
		self.student1 = self._create_user(f"student1_{self.test_id}@example.com", "Ashley", "Smith", ["LMS Student"])
		self.student2 = self._create_user(f"student2_{self.test_id}@example.com", "John", "Doe", ["LMS Student"])
		self.admin = self._create_user(
			f"frappe_{self.test_id}@example.com", "Frappe", "Admin", ["Moderator", "Course Creator", "Batch Evaluator"]
		)
		
		# Crear curso
		self.course = self._create_course(title=f"Utility Course {self.test_id}", instructor=self.admin.email)
		
		# Crear evaluaciones
		self.questions = self._create_quiz_questions()
		self.quiz = self._create_quiz(title=f"Utility Quiz {self.test_id}")
		self.assignment = self._create_assignment(title=f"Utility Assignment {self.test_id}")
		self.programming_exercise = self._create_programming_exercise(title=f"Utility Programming Exercise {self.test_id}")
		
		# Crear capítulos y lecciones
		self._setup_chapters()

		# Crear inscripciones y progreso
		self._create_enrollment(self.student1.email, self.course.name)
		self._add_student_progress(self.student1.email, self.course.name)
		self._create_enrollment(self.student2.email, self.course.name)
		self._add_student_progress(self.student2.email, self.course.name)

		self._add_rating(self.course.name, self.student1.email, 0.8, "Good course")
		self._add_rating(self.course.name, self.student2.email, 1, "Excellent course")

		self._create_certificate(self.course.name, self.student1.email)

	def test_export_course_as_zip(self):
		"""
		INT-015: Exportar un curso y verificar que el archivo ZIP contiene toda
		la estructura esperada (curso, capítulos, lecciones, evaluaciones).
		"""
		latest_file = self.get_latest_zip_file()
		self.assertTrue(latest_file, "No se generó el archivo ZIP de exportación")
		self.assertTrue(latest_file.endswith(".zip"), "El archivo exportado no tiene extensión .zip")

		# Validar el patrón del nombre del archivo exportado
		expected_name_pattern = re.escape(self.course.name) + r"_\d{8}_\d{6}_[a-f0-9]{8}\.zip"
		self.assertRegex(os.path.basename(latest_file), expected_name_pattern)

		# Inspeccionar el contenido del ZIP
		with zipfile.ZipFile(latest_file, "r") as zip_ref:
			file_list = zip_ref.namelist()
			
			# Comprobar archivos fundamentales
			self.assertIn("course.json", file_list, "Falta course.json en el ZIP")
			self.assertIn("instructors.json", file_list, "Falta instructors.json en el ZIP")

			# Comprobar que exportó capítulos
			chapter_files = [f for f in file_list if f.startswith("chapters/") and f.endswith(".json")]
			self.assertEqual(len(chapter_files), 3, "No se exportaron los 3 capítulos esperados")

			# Comprobar que exportó lecciones
			lesson_files = [f for f in file_list if f.startswith("lessons/") and f.endswith(".json")]
			self.assertEqual(len(lesson_files), 12, "No se exportaron las 12 lecciones esperadas")

			# Comprobar que exportó evaluaciones (cuestionarios, tareas, ejercicios)
			assessment_files = [
				f for f in file_list 
				if f.startswith("assessments/") and f.endswith(".json") and len(f.split("/")) == 2
			]
			self.assertEqual(len(assessment_files), 3, "No se exportaron las 3 evaluaciones esperadas")

	def test_import_course_from_zip(self):
		"""
		INT-016: Importar un curso desde un ZIP exportado y comprobar que se
		crea correctamente la estructura del curso duplicado.
		"""
		latest_file = self.get_latest_zip_file()
		self.assertTrue(latest_file, "No se pudo obtener el ZIP del curso original para importar")

		# Obtener la ruta del ZIP relativa al get_site_path() para la API de Frappe
		site_path = frappe.get_site_path()
		relative_zip_path = os.path.relpath(latest_file, site_path).replace("\\", "/")

		# Llamar a la API de importación
		imported_course_name = import_course_from_zip(relative_zip_path)
		self.assertTrue(imported_course_name, "La API no retornó el nombre del curso importado")

		# Obtener el documento del curso importado
		imported_course = frappe.get_doc("LMS Course", imported_course_name)

		# Verificar los datos generales
		self.assertEqual(imported_course.title, self.course.title)
		self.assertEqual(imported_course.category, self.course.category)
		self.assertEqual(len(imported_course.instructors), len(self.course.instructors))
		self.assertEqual(imported_course.instructors[0].instructor, self.course.instructors[0].instructor)

		# Verificar que los capítulos y lecciones se importaron
		self.assertTrue(len(imported_course.chapters) > 0, "El curso importado no tiene capítulos asociados")
		
		imported_first_chapter = frappe.get_doc("Course Chapter", imported_course.chapters[0].chapter)
		original_first_chapter = frappe.get_doc("Course Chapter", self.course.chapters[0].chapter)
		self.assertEqual(imported_first_chapter.title, original_first_chapter.title)

		self.assertTrue(len(imported_first_chapter.lessons) > 0, "El capítulo importado no tiene lecciones")
		
		imported_first_lesson = frappe.get_doc("Course Lesson", imported_first_chapter.lessons[0].lesson)
		original_first_lesson = frappe.get_doc("Course Lesson", original_first_chapter.lessons[0].lesson)
		self.assertEqual(imported_first_lesson.title, original_first_lesson.title)
		self.assertEqual(imported_first_lesson.content, original_first_lesson.content)

		# Limpiar el curso importado y sus dependencias para evitar polución de la BD de pruebas
		self.cleanup_imported_course(imported_course.name)

	def get_latest_zip_file(self):
		"""Auxiliar para disparar la exportación y retornar la ruta del ZIP generado."""
		export_course_as_zip(self.course.name)
		site_path = frappe.get_site_path("private", "files")
		zip_files = glob.glob(os.path.join(site_path, f"{self.course.name}_*.zip"))
		latest_file = max(zip_files, key=os.path.getctime) if zip_files else None
		return latest_file

	def cleanup_imported_course(self, course_name):
		"""Limpia el curso importado y sus evaluaciones secundarias."""
		self.cleanup_items.append(("LMS Course", course_name))
		self.cleanup_imported_assessment("LMS Quiz", self.quiz)
		self.cleanup_imported_assessment("LMS Assignment", self.assignment)
		self.cleanup_imported_assessment("LMS Programming Exercise", self.programming_exercise)

	def cleanup_imported_assessment(self, doctype, doc):
		"""Ubica y encola para eliminación los registros de evaluación duplicados por la importación."""
		imported_assessment = frappe.db.get_value(
			doctype, {"title": doc.title, "name": ["!=", doc.name]}, "name"
		)
		if imported_assessment:
			self.cleanup_items.append((doctype, imported_assessment))
