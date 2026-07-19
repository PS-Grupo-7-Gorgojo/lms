import frappe
from lms.lms.test_helpers import BaseTestUtils
from lms.lms.doctype.lms_certificate_evaluation.lms_certificate_evaluation import create_lms_certificate

class TestSecuritySECLMS005(BaseTestUtils):
	def setUp(self):
		super().setUp()

	def test_sec_lms_005_cannot_issue_certificate_without_approved_evaluation(self):
		"""
		SEC-LMS-005: Emisión de Certificados sin Evaluación Aprobada.
		Un estudiante con una evaluación con estatus "Failed" o "Pending" no debe poder
		crear e insertar un certificado ("LMS Certificate") para ese curso.
		"""
		test_id = frappe.generate_hash()[:8]
		student_email = f"student_sec5_{test_id}@example.com"

		# 1. Crear usuario estudiante
		self._create_user(
			email=student_email,
			first_name="LMS",
			last_name="Student",
			roles=["LMS Student"]
		)

		# 2. Crear evaluador
		evaluator = self._create_evaluator(f"evaluator_sec5_{test_id}@example.com")

		# 3. Crear curso de pago (paid_certificate = 1)
		course = frappe.new_doc("LMS Course")
		course.update({
			"title": f"Paid Cert Course {test_id}",
			"short_introduction": "Test course description",
			"description": "This is a detailed description of the Paid Cert Course.",
			"category": "Business",
			"published": 1,
			"paid_certificate": 1,
			"evaluator": evaluator.name,
			"timezone": "UTC",
			"course_price": 100,
			"currency": "USD",
			"instructors": [{"instructor": f"evaluator_sec5_{test_id}@example.com"}]
		})
		course.insert(ignore_permissions=True)
		self.cleanup_items.append(("LMS Course", course.name))

		# 4. Crear matriculación en el curso
		self._create_enrollment(student_email, course.name)

		# 5. Crear una evaluación con estatus "Failed" (rating > 0 obligatorio para Failed)
		eval_doc = frappe.get_doc({
			"doctype": "LMS Certificate Evaluation",
			"member": student_email,
			"course": course.name,
			"evaluator": evaluator.name,
			"status": "Fail",
			"rating": 2,
			"date": frappe.utils.nowdate(),
			"start_time": "10:00:00",
			"end_time": "11:00:00"
		})
		eval_doc.insert(ignore_permissions=True)
		self.cleanup_items.append(("LMS Certificate Evaluation", eval_doc.name))

		# 6. Intentar generar e insertar el certificado a partir de la evaluación fallida
		# Se realiza como Administrador para probar específicamente la lógica del validador (validate_criteria)
		from lms.lms.doctype.lms_certificate.lms_certificate import get_default_certificate_template
		cert_doc = create_lms_certificate(eval_doc.name)
		cert_doc.template = get_default_certificate_template()
		
		# Intentar insertar el certificado
		# El sistema debería lanzar una excepción de validación porque la evaluación no está aprobada
		with self.assertRaises(frappe.ValidationError):
			cert_doc.insert(ignore_permissions=False)
