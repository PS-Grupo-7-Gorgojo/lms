"""
Pruebas de integración para Módulo 4: Matrículas y Progreso
Casos: INT-006 (Completar lección crea progreso automático)
       INT-023: Matricularse a curso ya completado
	   INT-025: Concurrencia en último cupo
"""
import os
import unittest

import frappe
# from frappe.tests import IntegrationTestCase
from lms.lms.test_helpers import BaseTestUtils

@unittest.skipUnless(os.environ.get("RUN_INTEGRATION_TESTS"), "Skipping integration tests")
class TestEnrollmentProgress(BaseTestUtils):
    """
    Prueba de integración para la relación Enrollment → Course Progress
    Verifica que al completar la primera lección, se cree automáticamente el progreso
    """

    def setUp(self):
        """Configuración antes de CADA prueba"""
        super().setUp()
        frappe.set_user("Administrator")

        # 1. Crear curso
        self.course_title = f"Curso para Progreso {frappe.generate_hash(length=6)}"
        course = frappe.get_doc({
            "doctype": "LMS Course",
            "title": self.course_title,
            "course_name": self.course_title,
            "published": 1,
            "short_introduction": "Curso de prueba para progreso",
            "description": "Este curso se utiliza para probar el progreso automático"
        })
        course.append("instructors", {"instructor": "Administrator"})
        course.insert()
        self.course_name = course.name
        print(f" Curso '{self.course_title}' creado (ID: {self.course_name})")

        # 2. Crear capítulo CON referencia en el curso
        chapter = frappe.get_doc({
            "doctype": "Course Chapter",
            "title": "Capítulo 1: Fundamentos",
            "course": self.course_name,
            "is_scorm_package": 0
        })
        chapter.flags.ignore_links = True
        chapter.insert()
        self.chapter_name = chapter.name

        chapter_ref = frappe.get_doc({
            "doctype": "Chapter Reference",
            "chapter": self.chapter_name,
            "parent": self.course_name,
            "parenttype": "LMS Course",
            "parentfield": "chapters",
            "idx": 1
        })
        chapter_ref.flags.ignore_links = True
        chapter_ref.insert()
        print(f" Capítulo '{self.chapter_name}' creado y referenciado en el curso")

        # 3. Crear lección CON referencia en el capítulo
        lesson = frappe.get_doc({
            "doctype": "Course Lesson",
            "title": "Lección 1: Introducción",
            "chapter": self.chapter_name,
            "course": self.course_name
        })
        lesson.flags.ignore_links = True
        lesson.insert()
        self.lesson_name = lesson.name

        lesson_ref = frappe.get_doc({
            "doctype": "Lesson Reference",
            "lesson": self.lesson_name,
            "parent": self.chapter_name,
            "parenttype": "Course Chapter",
            "parentfield": "lessons",
            "idx": 1
        })
        lesson_ref.flags.ignore_links = True
        lesson_ref.insert()
        print(f" Lección '{self.lesson_name}' creada y referenciada en el capítulo")

        # 4. Crear usuario estudiante
        self.student_email = f"test_student_progress_{frappe.generate_hash(length=6)}@example.com"
        user = frappe.get_doc({
            "doctype": "User",
            "email": self.student_email,
            "first_name": "Test",
            "last_name": "Student Progress",
            "send_welcome_email": 0
        })
        user.insert()
        user.add_roles("LMS Student")
        print(f" Usuario '{self.student_email}' creado con rol LMS Student")

    def tearDown(self):
        """Limpieza después de CADA prueba"""
        frappe.db.rollback()
        super().tearDown()

    # ======================================================================
	# INT-005: Matrícula de estudiante
	# ======================================================================

    def test_int_005_student_enrollment(self):
	    """
	    INT-005: Verificar que un estudiante con rol LMS Student
	    pueda matricularse en un curso público existente
	    """
	    print("\n" + "="*70)
	    print(">  INT-005: Matrícula de estudiante")
	    print("="*70)

	    # --- 1. Verificar curso creado en setUp ---
	    print("\nPaso 1: Verificar curso base")
	    course = frappe.get_doc("LMS Course", self.course_name)
	    self.assertIsNotNone(course)
	    self.assertEqual(course.published, 1, "El curso no está publicado")
	    print(f"     Curso encontrado: {course.name} (Publicado: {course.published})")

	    # --- 2. Verificar usuario estudiante ---
	    print("\nPaso 2: Verificar usuario estudiante")
	    user = frappe.get_doc("User", self.student_email)
	    self.assertIsNotNone(user)
	    roles = frappe.get_roles(user.name)
	    self.assertIn("LMS Student", roles, "El usuario no tiene rol LMS Student")
	    print(f"     Usuario encontrado: {user.email}")
	    print(f"     Rol LMS Student: {'LMS Student' in roles}")

	    # --- 3. Verificar que NO hay matrícula previa ---
	    print("\nPaso 3: Verificar que NO hay matrícula previa")
	    existing_enrollment = frappe.db.exists(
	        "LMS Enrollment",
	        {"member": self.student_email, "course": self.course_name}
	    )
	    self.assertFalse(existing_enrollment, "Ya existe una matrícula previa")
	    print("     No hay matrícula previa")

	    # --- 4. Crear matrícula usando frappe.client.insert ---
	    print("\nPaso 4: Crear matrícula")
	    enrollment = frappe.client.insert({
	        "doctype": "LMS Enrollment",
	        "member": self.student_email,
	        "course": self.course_name
	    })
	    frappe.db.commit()

	    self.assertIsNotNone(enrollment)
	    self.assertEqual(enrollment.get("doctype"), "LMS Enrollment")
	    self.assertEqual(enrollment.get("member"), self.student_email)
	    self.assertEqual(enrollment.get("course"), self.course_name)
	    print(f"     Matrícula creada: {enrollment.get('name')}")

	    # --- 5. Verificar que la matrícula existe en la BD ---
	    print("\nPaso 5: Verificar matrícula en la base de datos")
	    enrollment_doc = frappe.get_doc("LMS Enrollment", enrollment.get("name"))
	    self.assertEqual(enrollment_doc.member, self.student_email)
	    self.assertEqual(enrollment_doc.course, self.course_name)
	    #  El campo status no existe en LMS Enrollment
	    print(f"     Matrícula verificada en BD")
	    print(f"       Estudiante: {enrollment_doc.member}")
	    print(f"       Curso: {enrollment_doc.course}")
	    print(f"       Progreso: {enrollment_doc.progress}%")

	    # --- 6. Verificar que NO hay duplicado ---
	    print("\nPaso 6: Verificar que no se permite duplicado")
	    with self.assertRaises(Exception) as context:
	        frappe.client.insert({
	            "doctype": "LMS Enrollment",
	            "member": self.student_email,
	            "course": self.course_name
	        })
	        frappe.db.commit()

	    error_msg = str(context.exception).lower()
	    self.assertTrue(
	        "already enrolled" in error_msg or "duplicate" in error_msg,
	        f"El error no menciona 'already enrolled'. Error: {error_msg}"
	    )
	    print(f"     Duplicado rechazado correctamente")

	    print("\n" + "="*70)
	    print("(n.n) INT-005: Prueba completada exitosamente")
	    print("   - Estudiante matriculado correctamente")
	    print("   - Matrícula verificada en base de datos")
	    print("   - Duplicado rechazado")
	    print("="*70)

    # ======================================================================
    # INT-006: Completar lección crea progreso automático
    # ====================================================================

    def test_int_006_lesson_completion_creates_progress(self):
        """
        INT-006: Verificar que al completar la primera lección, se crea automáticamente el progreso
        """
        print("\n" + "="*70)
        print("🧪 INT-006: Completar lección crea progreso automático")
        print("="*70)

        # 1. Crear matrícula
        print("\nPaso 1: Crear matrícula")
        enrollment = frappe.get_doc({
            "doctype": "LMS Enrollment",
            "member": self.student_email,
            "course": self.course_name
        })
        enrollment.flags.ignore_links = True
        enrollment.insert()
        frappe.db.commit()
        print(f"     Matrícula creada: {enrollment.name}")

        # 2. Verificar que NO existe progreso después de la matrícula
        print("\nPaso 2: Verificar que NO existe progreso después de la matrícula")
        progress_after_enrollment = frappe.db.exists(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name
            }
        )
        self.assertFalse(progress_after_enrollment,
            "El progreso existe después de la matrícula (comportamiento incorrecto)")
        print("    No existe progreso después de la matrícula (comportamiento esperado)")

        # 3. Completar la primera lección
        print("\nPaso 3: Completar la primera lección")
        from lms.lms.doctype.course_lesson.course_lesson import save_progress

        frappe.set_user(self.student_email)
        result = save_progress(self.lesson_name, self.course_name)
        frappe.db.commit()
        print(f"    Lección '{self.lesson_name}' completada (resultado: {result})")

        # 4. Verificar que el progreso se creó
        print("\nPaso 4: Verificar que el progreso se creó automáticamente")
        progress = frappe.db.get_value(
            "LMS Course Progress",
            {
                "member": self.student_email,
                "course": self.course_name
            },
            ["name", "status"],
            as_dict=True
        )

        self.assertIsNotNone(progress,
            "[x] No se creó automáticamente el registro de progreso al completar la lección")
        print(f"    Progreso creado automáticamente: {progress.name}")
        print(f"    Status: {progress.status}")

        # 5. Verificar relaciones
        print("\nPaso 5: Verificar relaciones del progreso")
        progress_doc = frappe.get_doc("LMS Course Progress", progress.name)

        self.assertEqual(progress_doc.member, self.student_email,
            "El progreso no está vinculado al estudiante correcto")
        self.assertEqual(progress_doc.course, self.course_name,
            "El progreso no está vinculado al curso correcto")
        self.assertEqual(progress_doc.lesson, self.lesson_name,
            "El progreso no está vinculado a la lección correcta")
        self.assertEqual(progress_doc.status, "Complete",
            "El estado del progreso no es 'Complete'")

        print(f"  (n.n) Progreso vinculado a estudiante: {progress_doc.member}")
        print(f"  (n.n) Progreso vinculado a curso: {progress_doc.course}")
        print(f"  (n.n) Progreso vinculado a lección: {progress_doc.lesson}")
        print(f"  (n.n) Estado: {progress_doc.status}")

        print("\n" + "="*70)
        print("(n.n) INT-006: Prueba completada exitosamente")
        print("="*70)

	# ======================================================================
	# INT-023: Matricularse a curso ya completado
	# ======================================================================

    def test_int_023_enroll_in_completed_course(self):
	    """
	    INT-023: Verificar que no se pueda matricular en un curso ya completado
	    o que se maneje correctamente la duplicación
	    """
	    print("\n" + "="*70)
	    print(">  INT-023: Matricularse a curso ya completado")
	    print("="*70)

	    # --- 1. Crear curso con capítulos y lecciones ---
	    print("\nPaso 1: Crear curso con capítulo y lección")
	    # Reutilizar el curso creado en setUp (self.course_name, self.chapter_name, self.lesson_name)
	    print(f"    Curso: {self.course_name}")
	    print(f"    Lección: {self.lesson_name}")

	    # --- 2. Crear matrícula inicial ---
	    print("\nPaso 2: Crear matrícula inicial")
	    enrollment = frappe.get_doc({
	        "doctype": "LMS Enrollment",
	        "member": self.student_email,
	        "course": self.course_name
	    })
	    enrollment.flags.ignore_links = True
	    enrollment.insert()
	    frappe.db.commit()
	    print(f"    Matrícula inicial creada: {enrollment.name}")

	    # --- 3. Completar el curso al 100% ---
	    print("\nPaso 3: Completar el curso al 100%")
	    from lms.lms.doctype.course_lesson.course_lesson import save_progress

	    frappe.set_user(self.student_email)

	    # Completar la lección
	    result = save_progress(self.lesson_name, self.course_name)
	    frappe.db.commit()
	    print(f"    Lección completada (resultado: {result})")

	    # Verificar progreso 100%
	    enrollment.reload()
	    self.assertEqual(enrollment.progress, 100)
	    print(f"    Progreso del curso: {enrollment.progress}%")

	    # --- 4. Intentar matricular nuevamente (debe fallar) ---
	    print("\nPaso 4: Intentar matricular nuevamente (debe fallar)")
	    frappe.set_user(self.student_email)

	    try:
	        # Intentar crear una segunda matrícula
	        enrollment2 = frappe.get_doc({
	            "doctype": "LMS Enrollment",
	            "member": self.student_email,
	            "course": self.course_name
	        })
	        enrollment2.flags.ignore_links = True
	        enrollment2.insert()
	        frappe.db.commit()

	        # Si llega aquí, la prueba falla (no debería permitir duplicado)
	        self.fail("Se permitió crear una segunda matrícula en un curso ya completado")

	    except Exception as e:
	        error_msg = str(e).lower()
	        print(f"    Error capturado correctamente: {str(e)[:150]}")

	        # Verificar que el error menciona duplicado o completado
	        # La validación está en validate_duplicate_enrollment()
	        self.assertTrue(
	            "already enrolled" in error_msg or "duplicate" in error_msg or "exists" in error_msg,
	            f"El mensaje de error no menciona 'already enrolled'. Error: {error_msg}"
	        )
	        print("    [>] Error capturado correctamente (matrícula duplicada)")

	    # --- 5. Verificar que solo existe una matrícula ---
	    print("\nPaso 5: Verificar que solo existe una matrícula")
	    frappe.set_user("Administrator")
	    enrollments = frappe.get_all(
	        "LMS Enrollment",
	        {"member": self.student_email, "course": self.course_name}
	    )
	    self.assertEqual(len(enrollments), 1,
	        f"Se encontraron {len(enrollments)} matrículas en lugar de 1")
	    print(f"    [>] Solo existe 1 matrícula para el curso")

	    print("\n" + "="*70)
	    print("(n.n) INT-023: Prueba completada exitosamente")
	    print("="*70)

	# ======================================================================
	# INT-025: Concurrencia en último cupo
	# ======================================================================

    # def test_int_025_concurrent_enrollment_last_seat(self):
	   #  """
	   #  INT-025: Verificar que con cupo de 1 estudiante y 2 requests concurrentes,
	   #  solo una matrícula sea exitosa y la otra rechazada con "Course is full"
	   #  """
	   #  print("\n" + "="*70)
	   #  print(">  INT-025: Concurrencia en último cupo")
	   #  print("="*70)

	   #  # --- 1. Crear curso con cupo limitado (seat_count=1) ---
	   #  print("\nPaso 1: Crear curso con cupo para 1 estudiante")

	   #  course_title = f"Curso Cupo {frappe.generate_hash(length=6)}"
	   #  course = frappe.get_doc({
	   #      "doctype": "LMS Course",
	   #      "title": course_title,
	   #      "published": 1,
	   #      "seat_count": 1,
	   #      "short_introduction": "Curso con cupo limitado",
	   #      "description": "Curso para probar concurrencia en último cupo"
	   #  })
	   #  course.append("instructors", {"instructor": "Administrator"})
	   #  course.insert()
	   #  course_name = course.name
	   #  print(f"    Curso '{course_title}' creado (ID: {course_name})")
	   #  print(f"    Cupo máximo: 1")

	   #  # --- 2. Crear capítulo y lección ---
	   #  print("\nPaso 2: Crear capítulo y lección")
	   #  chapter = frappe.get_doc({
	   #      "doctype": "Course Chapter",
	   #      "title": "Capítulo 1",
	   #      "course": course_name,
	   #      "is_scorm_package": 0
	   #  })
	   #  chapter.flags.ignore_links = True
	   #  chapter.insert()

	   #  chapter_ref = frappe.get_doc({
	   #      "doctype": "Chapter Reference",
	   #      "chapter": chapter.name,
	   #      "parent": course_name,
	   #      "parenttype": "LMS Course",
	   #      "parentfield": "chapters",
	   #      "idx": 1
	   #  })
	   #  chapter_ref.flags.ignore_links = True
	   #  chapter_ref.insert()

	   #  lesson = frappe.get_doc({
	   #      "doctype": "Course Lesson",
	   #      "title": "Lección 1",
	   #      "chapter": chapter.name,
	   #      "course": course_name
	   #  })
	   #  lesson.flags.ignore_links = True
	   #  lesson.insert()

	   #  lesson_ref = frappe.get_doc({
	   #      "doctype": "Lesson Reference",
	   #      "lesson": lesson.name,
	   #      "parent": chapter.name,
	   #      "parenttype": "Course Chapter",
	   #      "parentfield": "lessons",
	   #      "idx": 1
	   #  })
	   #  lesson_ref.flags.ignore_links = True
	   #  lesson_ref.insert()
	   #  frappe.db.commit()
	   #  print(f"    Capítulo y lección creados")

	   #  # --- 3. Crear 2 estudiantes ---
	   #  print("\nPaso 3: Crear 2 estudiantes")
	   #  student1_email = f"test_student_conc1_{frappe.generate_hash(length=6)}@example.com"
	   #  student2_email = f"test_student_conc2_{frappe.generate_hash(length=6)}@example.com"

	   #  for email in [student1_email, student2_email]:
	   #      user = frappe.get_doc({
	   #          "doctype": "User",
	   #          "email": email,
	   #          "first_name": "Test",
	   #          "last_name": f"Concurrent {email[:6]}",
	   #          "send_welcome_email": 0
	   #      })
	   #      user.insert()
	   #      user.add_roles("LMS Student")
	   #  frappe.db.commit()
	   #  print(f"    Estudiante 1: {student1_email}")
	   #  print(f"    Estudiante 2: {student2_email}")

	   #  # --- 4. Definir función para matricular (sin threading) ---
	   #  enrollments_created = []
	   #  errors = []

	   #  def enroll_student(email):
	   #      try:
	   #          enrollment = frappe.get_doc({
	   #              "doctype": "LMS Enrollment",
	   #              "member": email,
	   #              "course": course_name
	   #          })
	   #          enrollment.flags.ignore_links = True
	   #          enrollment.insert()
	   #          frappe.db.commit()
	   #          enrollments_created.append(email)
	   #          return True
	   #      except Exception as e:
	   #          frappe.db.rollback()
	   #          errors.append(str(e))
	   #          return False

	   #  # --- 5. Simular concurrencia (sin threads) ---
	   #  print("\nPaso 4: Simular concurrencia (requests simultáneas)")
	   #  # Ejecutar ambas funciones "simultáneamente" (una después de otra, pero con commits intermedios)

	   #  # Primero, intentar matricular al estudiante 1
	   #  success1 = enroll_student(student1_email)

	   #  # Luego, intentar matricular al estudiante 2 (debería fallar si el cupo está lleno)
	   #  success2 = enroll_student(student2_email)

	   #  # --- 6. Verificar solo 1 matrícula exitosa ---
	   #  print("\nPaso 5: Verificar solo 1 matrícula exitosa")
	   #  print(f"    Estudiante 1: {' Éxito' if success1 else '[X] Falló'}")
	   #  print(f"    Estudiante 2: {' Éxito' if success2 else '[X] Falló'}")

	   #  success_count = sum([1 for s in [success1, success2] if s])
	   #  self.assertEqual(success_count, 1, f"Se crearon {success_count} matrículas exitosas en lugar de 1")
	   #  print(f"     Solo 1 matrícula fue exitosa")

	   #  # --- 7. Verificar error de cupo ---
	   #  print("\nPaso 6: Verificar mensaje de error")
	   #  if errors:
	   #      error_msg = errors[0].lower()
	   #      print(f"    Error capturado: {error_msg[:150]}...")

	   #      self.assertTrue(
	   #          "full" in error_msg or "seat" in error_msg or "already" in error_msg or "duplicate" in error_msg,
	   #          f"El error no menciona 'full', 'seat' o 'already'. Error: {error_msg}"
	   #      )
	   #      print("     Error correcto (curso lleno o duplicado)")
	   #  else:
	   #      # Si no hay errores, verificar que solo hay una matrícula
	   #      enrollments = frappe.get_all("LMS Enrollment", {"course": course_name})
	   #      self.assertEqual(len(enrollments), 1, f"Se encontraron {len(enrollments)} matrículas")
	   #      print("     No hay errores, pero solo 1 matrícula creada (comportamiento esperado)")

	   #  # --- 8. Verificar solo 1 matrícula en la BD ---
	   #  print("\nPaso 7: Verificar solo 1 matrícula en la base de datos")
	   #  frappe.set_user("Administrator")
	   #  enrollments = frappe.get_all(
	   #      "LMS Enrollment",
	   #      {"course": course_name}
	   #  )
	   #  self.assertEqual(len(enrollments), 1, f"Se encontraron {len(enrollments)} matrículas en lugar de 1")
	   #  print(f"     Solo 1 matrícula registrada en la BD")

	   #  # --- 9. Limpiar datos de prueba ---
	   #  print("\nPaso 8: Limpiar datos de prueba")
	   #  for enrollment in frappe.get_all("LMS Enrollment", {"course": course_name}):
	   #      frappe.delete_doc("LMS Enrollment", enrollment.name, force=True, ignore_permissions=True)

	   #  for email in [student1_email, student2_email]:
	   #      if frappe.db.exists("User", email):
	   #          frappe.delete_doc("User", email, force=True, ignore_permissions=True)

	   #  if frappe.db.exists("LMS Course", course_name):
	   #      course_doc = frappe.get_doc("LMS Course", course_name)
	   #      for chapter_ref in course_doc.get("chapters", []):
	   #          chapter_name = chapter_ref.get("chapter")
	   #          if chapter_name and frappe.db.exists("Course Chapter", chapter_name):
	   #              chapter_doc = frappe.get_doc("Course Chapter", chapter_name)
	   #              for lesson_ref in chapter_doc.get("lessons", []):
	   #                  lesson_name = lesson_ref.get("lesson")
	   #                  if lesson_name and frappe.db.exists("Course Lesson", lesson_name):
	   #                      frappe.delete_doc("Course Lesson", lesson_name, force=True, ignore_permissions=True)
	   #              frappe.delete_doc("Course Chapter", chapter_name, force=True, ignore_permissions=True)
	   #      frappe.delete_doc("LMS Course", course_name, force=True, ignore_permissions=True)
	   #  frappe.db.commit()
	   #  print("     Datos de prueba eliminados")

	   #  print("\n" + "="*70)
	   #  print("(n.n) INT-025: Prueba completada exitosamente")
	   #  print("   - 2 requests concurrentes con cupo=1")
	   #  print("   - Solo 1 matrícula exitosa")
	   #  print("   - La otra rechazada (curso lleno o duplicado)")
	   #  print("="*70)

