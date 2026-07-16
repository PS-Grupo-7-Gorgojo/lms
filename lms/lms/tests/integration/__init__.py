import frappe
try:
	import frappe.core.doctype.user.user as user_module
	user_module.throttle_user_creation = lambda: None
except Exception:
	pass

from .test_import_export import TestImportExportIntegration
from .test_permissions import TestPermissionsIntegration
from .test_batch import TestBatchIntegration
from .test_enrollment import TestEnrollmentProgress
from .test_badges import TestBadgeEnrollment
from .test_certificates import TestCertificateCompletion
from .test_course_deletion import TestCourseDeletion
from .test_evaluations import TestQuizValidation
from .test_search import TestSearchIntegration
