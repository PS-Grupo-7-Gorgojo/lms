"""
Utilidades para pruebas de integración.
"""

import frappe
from .api_client import APIClient

class IntegrationTestUtils:
    """
    Utilidades para pruebas de integración.
    Proporciona métodos para crear datos de prueba sin depender de fixtures de Frappe.
    """

    def __init__(self, base_url="http://localhost:8000", user="Administrator", password="admin"):
        self.base_url = base_url
        self.api_client = APIClient(base_url, user, password)
        self.test_course = None
        self.test_student = None
        self._setup_test_data()

    def _setup_test_data(self):
        """Crea datos de prueba básicos (curso, usuario, etc.)"""
        # 1. Crear curso de prueba si no existe
        course_name = "test-course-integration"
        response = self.api_client.get_doc("LMS Course", course_name)

        if response.status_code != 200:
            # Crear curso usando la API REST
            response = self.api_client.create_doc("LMS Course", {
                "title": "Curso de Prueba Integración",
                "course_name": course_name,
                "published": 1,
                "upcoming": 0
            })
            if response.status_code == 200:
                print(f"Curso '{course_name}' creado")
            else:
                print(f"No se pudo crear el curso: {response.text}")
        else:
            print(f"Curso '{course_name}' ya existe")

        self.test_course = course_name

        # 2. Crear usuario de prueba si no existe
        student_email = "test_student_integration@example.com"
        response = self.api_client.get_doc("User", student_email)
        if response.status_code != 200:
            response = self.api_client.create_doc("User", {
                "email": student_email,
                "first_name": "Test",
                "last_name": "Student Integration",
                "send_welcome_email": 0
            })
            if response.status_code == 200:
                print(f"Usuario '{student_email}' creado")
            else:
                print(f"No se pudo crear el usuario: {response.text}")
        else:
            print(f"Usuario '{student_email}' ya existe")

        self.test_student = student_email

    def cleanup_course(self, course_name):
        """Limpia un curso y todos sus capítulos/lecciones usando la API"""
        # Primero obtener el curso para ver sus capítulos
        response = self.api_client.get_doc("LMS Course", course_name)
        if response.status_code != 200:
            return

        course_data = response.json().get("data", {})

        # Eliminar capítulos
        for chapter_ref in course_data.get("chapters", []):
            chapter_name = chapter_ref.get("chapter")
            if chapter_name:
                # Eliminar capítulo
                delete_url = f"{self.base_url}/api/method/lms.lms.api.delete_chapter"
                self.api_client.session.post(delete_url, json={"chapter": chapter_name})
                print(f"  - Capítulo '{chapter_name}' eliminado")

        # Eliminar curso
        delete_url = f"{self.base_url}/api/resource/LMS%20Course/{course_name}"
        response = self.api_client.session.delete(delete_url)
        if response.status_code in [200, 202]:
            print(f"Curso '{course_name}' eliminado")
        else:
            print(f"No se pudo eliminar el curso: {response.text}")
