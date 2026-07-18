"""
Pruebas de integración para Módulo 3: Cursos y Contenido
Casos: INT-003 (Crear jerarquía completa de curso)
       INT-004 (Asignar múltiples instructores a un curso)
"""
import os
import unittest

import frappe
from lms.lms.test_helpers import BaseTestUtils


@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestCourseChapterIntegration(BaseTestUtils):
	"""
	Clase para pruebas de integración del Módulo 3: Cursos y Contenido.
	Cubre los casos:
	- INT-003: Crear jerarquía completa de curso (Course → Chapter → Lesson) por un Course Creator.
	- INT-004: Asignar múltiples instructores a un curso y validar permisos de edición.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_create_complete_course_hierarchy(self):
		"""
		INT-003: Crear jerarquía completa de curso (Course -> Chapter -> Lesson)
		con un usuario que posee el rol de 'Course Creator'.
		Se debe verificar que se creen correctamente y con las relaciones esperadas.
		"""
		test_id = frappe.generate_hash()[:8]
		creator_email = f"creator_{test_id}@example.com"

		# 1. Crear el usuario Course Creator
		self._create_user(
			email=creator_email,
			first_name="Course",
			last_name="Creator",
			roles=["Course Creator"]
		)

		# Cambiar la sesión activa al usuario Course Creator
		frappe.set_user(creator_email)

		try:
			# 2. Crear el curso (LMS Course)
			course_title = f"Course {test_id}"
			course = self._create_course(title=course_title, instructor=creator_email)
			self.assertTrue(frappe.db.exists("LMS Course", course.name))

			# 3. Crear el capítulo (Course Chapter)
			chapter_title = f"Chapter {test_id}"
			chapter = self._create_chapter(title=chapter_title, course=course.name)
			self.assertTrue(frappe.db.exists("Course Chapter", chapter.name))

			# Relacionar el capítulo al curso agregándolo a su tabla de capítulos
			course.reload()
			if not any(c.chapter == chapter.name for c in course.chapters):
				course.append("chapters", {"chapter": chapter.name})
			course.save()

			# 4. Crear la lección (Course Lesson) con contenido
			lesson_title = f"Lesson {test_id}"
			content_json = '{"time":1765194986690,"blocks":[{"id":"dkLzbW14ds","type":"markdown","data":{"text":"Test content for INT-003"}},{"id":"KBwuWPc8rV","type":"markdown","data":{"text":""}}],"version":"2.29.0"}'
			lesson = self._create_lesson(title=lesson_title, chapter=chapter.name, course=course.name, content=content_json)
			self.assertTrue(frappe.db.exists("Course Lesson", lesson.name))

			# Relacionar la lección al capítulo agregándolo a su tabla de lecciones
			chapter_doc = frappe.get_doc("Course Chapter", chapter.name)
			if not any(l.lesson == lesson.name for l in chapter_doc.lessons):
				chapter_doc.append("lessons", {"lesson": lesson.name})
			chapter_doc.save()

			# 5. Verificaciones finales de la jerarquía y relaciones
			course.reload()
			chapter_doc.reload()
			lesson_doc = frappe.get_doc("Course Lesson", lesson.name)

			# Verificar que el capítulo apunta al curso correcto
			self.assertEqual(chapter_doc.course, course.name)
			# Verificar que el curso contiene el capítulo en sus chapters
			self.assertTrue(any(c.chapter == chapter.name for c in course.chapters))

			# Verificar que la lección apunta al capítulo y curso correctos
			self.assertEqual(lesson_doc.chapter, chapter.name)
			self.assertEqual(lesson_doc.course, course.name)
			# Verificar que el capítulo contiene la lección en sus lessons
			self.assertTrue(any(l.lesson == lesson.name for l in chapter_doc.lessons))
			# Verificar contenido de la lección
			self.assertEqual(lesson_doc.content, content_json)

		finally:
			# Restaurar el usuario activo a Administrator
			frappe.set_user("Administrator")

	def test_assign_multiple_instructors(self):
		"""
		INT-004: Asignar múltiples instructores a un curso.
		Verificar que todos los instructores agregados tengan permiso de edición (can_modify_course).
		"""
		test_id = frappe.generate_hash()[:8]

		# 1. Crear un curso
		course_title = f"Course Multi Instructors {test_id}"
		course = self._create_course(title=course_title, instructor="admin@example.com")
		self.assertTrue(frappe.db.exists("LMS Course", course.name))

		# 2. Crear múltiples usuarios instructores con rol Course Creator
		instructor_emails = [
			f"inst1_{test_id}@example.com",
			f"inst2_{test_id}@example.com",
			f"inst3_{test_id}@example.com"
		]

		for email in instructor_emails:
			self._create_user(
				email=email,
				first_name="Instructor",
				last_name=email.split("@")[0],
				roles=["Course Creator"]
			)

		# 3. Asignar múltiples instructores a la tabla del curso
		course.reload()
		course.instructors = []
		for email in instructor_emails:
			course.append("instructors", {"instructor": email})
		course.save()

		# 4. Validar permisos de edición (can_modify_course y frappe.has_permission) para cada instructor
		from lms.lms.utils import can_modify_course

		for email in instructor_emails:
			frappe.set_user(email)
			try:
				# can_modify_course debe retornar True
				self.assertTrue(can_modify_course(course.name), f"Instructor {email} should be able to modify the course.")
				
				# El documento cargado bajo el usuario instructor debe pasar la verificación de permisos de escritura
				doc = frappe.get_doc("LMS Course", course.name)
				self.assertTrue(frappe.has_permission("LMS Course", "write", doc=doc), f"Instructor {email} should have write permission.")
			finally:
				frappe.set_user("Administrator")

		# 5. Validar que un usuario sin rol de instructor no tenga permisos de modificación
		guest_email = f"guest_{test_id}@example.com"
		self._create_user(
			email=guest_email,
			first_name="Guest",
			last_name="User",
			roles=["LMS Student"]
		)
		frappe.set_user(guest_email)
		try:
			self.assertFalse(can_modify_course(course.name), f"Guest {guest_email} should NOT be able to modify the course.")
		finally:
			frappe.set_user("Administrator")
