"""
Pruebas de integración para Módulo 1: Configuración de LMS Settings
Casos: INT-002 (Cambiar gateway de pagos de Razorpay a Stripe)
"""
import os
import unittest
from unittest.mock import patch, MagicMock

import frappe
from lms.lms.test_helpers import BaseTestUtils


@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestSettingsIntegration(BaseTestUtils):
	"""
	Clase para probar las configuraciones de LMS Settings e integraciones relacionadas.
	"""

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

		# Crear curso de prueba pagado
		self.course_title = f"Curso Settings Test {frappe.generate_hash(length=6)}"
		course = frappe.get_doc({
			"doctype": "LMS Course",
			"title": self.course_title,
			"published": 1,
			"paid_course": 1,
			"course_price": 100,
			"currency": "USD",
			"short_introduction": "Curso para prueba de settings",
			"description": "Curso para probar cambio de gateway"
		})
		course.append("instructors", {"instructor": "Administrator"})
		course.insert()
		self.course_name = course.name
		self.cleanup_items.append(("LMS Course", self.course_name))

		# Crear usuario estudiante
		self.student_email = f"test_student_settings_{frappe.generate_hash(length=6)}@example.com"
		user = frappe.get_doc({
			"doctype": "User",
			"email": self.student_email,
			"first_name": "Test",
			"last_name": "Settings Student",
			"send_welcome_email": 0
		})
		user.insert()
		user.add_roles("LMS Student")
		self.cleanup_items.append(("User", self.student_email))

		# Crear Source si existe
		if frappe.db.exists("DocType", "LMS Source"):
			source_name = f"test_source_{frappe.generate_hash(length=6)}"
			source = frappe.get_doc({
				"doctype": "LMS Source",
				"source": source_name,
				"source_name": source_name,
				"title": "Test Source"
			})
			source.insert(ignore_permissions=True)
			self.source_name = source.name
			self.cleanup_items.append(("LMS Source", self.source_name))
		else:
			self.source_name = None

		# Crear Address
		self.address_name = f"Test Address {frappe.generate_hash(length=6)}"
		address = frappe.get_doc({
			"doctype": "Address",
			"address_title": self.address_name,
			"address_line1": "123 Test Street",
			"city": "Test City",
			"country": "United States",
			"email_id": self.student_email
		})
		address.insert(ignore_permissions=True)
		self.address_name = address.name
		self.cleanup_items.append(("Address", self.address_name))

	@patch("lms.lms.payments.get_controller")
	def test_int_002_change_payment_gateway_to_stripe(self, mock_get_controller):
		"""
		INT-002: Cambiar gateway de pagos de Razorpay a Stripe.
		Verifica que el cambio se persista en LMS Settings y que
		get_payment_link invoque al controlador de Stripe.
		"""
		# Mock del controlador del gateway de Stripe
		mock_controller_instance = MagicMock()
		mock_controller_instance.get_payment_url.return_value = "https://stripe.com/pay/mock_session"
		mock_get_controller.return_value = mock_controller_instance

		# Guardar configuración actual
		lms_settings = frappe.get_doc("LMS Settings")
		old_gateway = lms_settings.payment_gateway

		# Cambiar gateway a Stripe
		lms_settings.payment_gateway = "Stripe"
		lms_settings.save(ignore_permissions=True)
		frappe.db.commit()

		try:
			# Validar que el cambio está persistido en la base de datos
			persisted_gateway = frappe.db.get_single_value("LMS Settings", "payment_gateway")
			self.assertEqual(persisted_gateway, "Stripe")

			# Preparar dirección de pago
			address = {
				"billing_name": "Test Settings Student",
				"address_line1": "123 Street",
				"city": "City",
				"country": "United States"
			}
			if self.source_name:
				address["source"] = self.source_name

			from lms.lms.payments import get_payment_link

			# Cambiar la sesión activa al estudiante de prueba
			frappe.set_user(self.student_email)

			# Solicitar link de pago
			url = get_payment_link(
				doctype="LMS Course",
				docname=self.course_name,
				address=address,
				payment_for_certificate=0
			)

			# Registrar el pago creado para limpieza
			payment_name = frappe.db.get_value("LMS Payment", {"member": self.student_email})
			if payment_name:
				self.cleanup_items.append(("LMS Payment", payment_name))

			# Verificar que se utilizó la configuración de Stripe (invoque al mock de Stripe)
			self.assertEqual(url, "https://stripe.com/pay/mock_session")
			mock_get_controller.assert_called_with("Stripe")

		finally:
			# Restaurar configuración original
			frappe.set_user("Administrator")
			lms_settings = frappe.get_doc("LMS Settings")
			lms_settings.payment_gateway = old_gateway
			lms_settings.save(ignore_permissions=True)
			frappe.db.commit()
