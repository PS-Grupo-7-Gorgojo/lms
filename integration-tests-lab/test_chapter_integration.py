import requests
import json
import sys

BASE_URL = "http://localhost:8000"
USER = "Administrator"
PASSWORD = "admin"
COURSE_NAME = "javascript-desde-cero"  # curso creado manualmente
UPSERT_CHAPTER_URL = f"{BASE_URL}/api/method/lms.lms.api.upsert_chapter"

def login():
    session = requests.Session()
    login_url = f"{BASE_URL}/api/method/login"
    response = session.post(login_url, json={"usr": USER, "pwd": PASSWORD})
    if response.status_code == 200:
        print("Login exitoso")
        return session
    else:
        print(f"Login falló: {response.status_code}")
        print(response.text)
        sys.exit(1)

def upsert_chapter(session, title, course, is_scorm_package=False, scorm_package=None):
    payload = {
        "title": title,
        "course": course,
        "is_scorm_package": is_scorm_package
    }
    if scorm_package is not None:
        payload["scorm_package"] = scorm_package
    response = session.post(UPSERT_CHAPTER_URL, json=payload, timeout=5)
    return response

# --- Casos de prueba ---

def caso1_sintactico(session):
    print("\n" + "="*60)
    print("TEST ::: Caso 1: Sintáctico – Falta el campo 'title'")
    print("="*60)
    payload = {"course": COURSE_NAME}
    response = session.post(UPSERT_CHAPTER_URL, json=payload, timeout=5)

    print(f"Payload enviado: {json.dumps(payload, indent=2)}")
    print(f"Status Code: {response.status_code}")
    print(f"Respuesta del servidor:\n{response.text}")

    if response.status_code == 400:
        print("Resultado: Validación funciona (400 Bad Request)")
        return "PASS"
    else:
        print("Resultado: Falló (no se rechazó la solicitud)")
        return "FAIL"

def caso2_semantico(session):
    print("\n" + "="*60)
    print("TEST ::: Caso 2: Semántico – SCORM sin paquete")
    print("="*60)
    payload = {
        "title": "Capítulo SCORM",
        "course": COURSE_NAME,
        "is_scorm_package": True
    }
    response = session.post(UPSERT_CHAPTER_URL, json=payload, timeout=5)

    print(f"Payload enviado: {json.dumps(payload, indent=2)}")
    print(f"Status Code: {response.status_code}")
    print(f"Respuesta del servidor:\n{response.text}")

    if response.status_code == 400:
        if "scorm_package" in response.text.lower():
            print("Resultado: Validación semántica correcta")
            return "PASS"
        else:
            print("Resultado: 400 pero el mensaje no especifica scorm_package")
            return "PARTIAL"
    else:
        print("Resultado: Falló (no se rechazó la solicitud)")
        return "FAIL"

def caso3_resiliencia(session):
    print("\n" + "="*60)
    print("TEST ::: Caso 3: Resiliencia – Timeout simulado")
    print("="*60)
    payload = {"title": "Timeout test", "course": COURSE_NAME}
    print(f"Payload enviado: {json.dumps(payload, indent=2)}")

    try:
        response = session.post(UPSERT_CHAPTER_URL, json=payload, timeout=0.001)
        print(f"Status Code: {response.status_code}")
        print(f"Respuesta del servidor:\n{response.text}")
        print("Resultado: No hubo timeout (el servidor respondió rápido o el timeout no se aplicó)")
        return "FAIL"
    except requests.exceptions.Timeout:
        print("Resultado: Timeout manejado correctamente (el cliente no colapsó)")
        return "PASS"
    except Exception as e:
        print(f"Resultado: Error inesperado: {e}")
        return "FAIL"

# --- Ejecución principal ---

if __name__ == "__main__":
    session = login()

    # Verificar que el curso existe
    check_url = f"{BASE_URL}/api/resource/LMS%20Course/{COURSE_NAME}"
    resp = session.get(check_url)
    if resp.status_code == 200:
        print(f"Curso '{COURSE_NAME}' encontrado.")
    else:
        print(f"No se encontró el curso '{COURSE_NAME}'. Verifica el nombre.")
        print(f"Respuesta: {resp.text}")
        sys.exit(1)

    resultados = []
    resultados.append(("Caso 1 (Sintáctico)", caso1_sintactico(session)))
    resultados.append(("Caso 2 (Semántico)", caso2_semantico(session)))
    resultados.append(("Caso 3 (Resiliencia)", caso3_resiliencia(session)))

    print("\n" + "="*60)
    print("_ _ _ REPORTE DE RESULTADOS DE PRUEBAS DE INTEGRACIÓN")
    print("="*60)
    print(f"{'Caso':<25} {'Resultado':<10}")
    print("-"*60)
    for caso, res in resultados:
        print(f"{caso:<25} {res:<10}")
    print("="*60)

    if any(res != "PASS" for _, res in resultados):
        print("\nSe detectaron discrepancias. Complete los reportes de incidentes:")
        for caso, res in resultados:
            if res != "PASS":
                print(f"  - {caso}: Resultado = {res}")
    else:
        print("\nTodos los casos pasaron correctamente.")
