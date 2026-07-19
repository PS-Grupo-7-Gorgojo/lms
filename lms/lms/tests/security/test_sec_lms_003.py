import io
import zipfile
import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.api import extract_package

class TestSecuritySECLMS003(BaseTestUtils):
	def setUp(self):
		super().setUp()

	def test_sec_lms_003_scorm_malicious_zip_is_rejected(self):
		"""
		SEC-LMS-003: Subida Insegura de Paquetes SCORM (XXE / XSS).
		Verificar que un paquete SCORM (ZIP) que contenga código malicioso (p. ej., XSS en HTML)
		sea detectado y rechazado por el sistema de seguridad.
		"""
		test_id = frappe.generate_hash()[:8]
		creator_email = f"creator_sec3_{test_id}@example.com"

		# 1. Crear usuario Course Creator
		self._create_user(
			email=creator_email,
			first_name="Course",
			last_name="Creator",
			roles=["Course Creator"]
		)

		# 2. Crear un curso
		course = self._create_course(
			title=f"SCORM Security Course {test_id}",
			instructor=creator_email
		)

		# 3. Crear un archivo ZIP en memoria con contenido malicioso
		zip_buffer = io.BytesIO()
		with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
			# Un archivo HTML con una carga XSS sospechosa
			malicious_html = '<html><body onload="javascript:alert(document.cookie)">SCORM Course</body></html>'
			zf.writestr("index.html", malicious_html)
			# imsmanifest.xml es requerido por SCORM parsing
			zf.writestr("imsmanifest.xml", "<manifest></manifest>")
		
		zip_data = zip_buffer.getvalue()

		# 4. Registrar el archivo ZIP en el gestor de archivos de Frappe
		file_doc = frappe.get_doc({
			"doctype": "File",
			"file_name": f"malicious_scorm_{test_id}.zip",
			"content": zip_data,
			"is_private": 1
		})
		file_doc.insert(ignore_permissions=True)
		self.cleanup_items.append(("File", file_doc.name))

		# 5. Cambiar el usuario de la sesión al Creador de Curso
		frappe.set_user(creator_email)

		try:
			# 6. Intentar extraer el paquete SCORM (debe lanzar una excepción de validación/seguridad)
			with self.assertRaises(frappe.ValidationError):
				# Llamar a extract_package con el archivo creado
				extract_package(course.name, f"Chapter Title {test_id}", frappe._dict({"name": file_doc.name}))
		finally:
			# Restaurar usuario
			frappe.set_user("Administrator")
