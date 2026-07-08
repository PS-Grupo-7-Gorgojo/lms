"""
Cliente HTTP para pruebas de integración.
Usa solo requests
"""

import requests
import json

class APIClient:
    """Cliente para hacer llamadas a la API de Frappe en pruebas de integración"""

    def __init__(self, base_url="http://localhost:8000", user="Administrator", password="admin"):
        self.base_url = base_url
        self.session = requests.Session()
        self.user = user

        # Autenticarse al iniciar
        self.login(user, password)

    def login(self, user, password):
        """Inicia sesión en el sitio"""
        login_url = f"{self.base_url}/api/method/login"
        response = self.session.post(login_url, json={"usr": user, "pwd": password})
        if response.status_code != 200:
            raise Exception(f"Login falló: {response.status_code} - {response.text}")
        print(f"Login exitoso como {user}")
        return response

    def post(self, method, payload, timeout=10):
        """Hace una solicitud POST a un método de la API"""
        url = f"{self.base_url}/api/method/{method}"
        response = self.session.post(url, json=payload, timeout=timeout)
        return response

    def get(self, method, params=None, timeout=10):
        """Hace una solicitud GET a un método de la API"""
        url = f"{self.base_url}/api/method/{method}"
        response = self.session.get(url, params=params, timeout=timeout)
        return response

    def create_doc(self, doctype, data):
        """Crea un documento usando la API REST estándar de Frappe"""
        url = f"{self.base_url}/api/resource/{doctype}"
        response = self.session.post(url, json=data)
        return response

    def get_doc(self, doctype, name):
        """Obtiene un documento usando la API REST estándar de Frappe"""
        url = f"{self.base_url}/api/resource/{doctype}/{name}"
        response = self.session.get(url)
        return response
