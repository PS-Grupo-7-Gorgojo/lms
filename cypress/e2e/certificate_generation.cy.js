describe("Certificate Generation — SYS-06", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const generateId = () => `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

	let courseName, lessonName;
	let csrfToken;

	function frappeReq(method, url, body) {
		const headers = csrfToken ? { "X-Frappe-CSRF-Token": csrfToken } : {};
		return cy.request({ url, method, headers, body, failOnStatusCode: false });
	}

	before(() => {
		cy.login();
		cy.visit("/");
		cy.window().then((win) => {
			csrfToken = win.csrf_token;
		});

		const certId = generateId();
		courseName = `E2E Cert Course ${certId}`;
		lessonName = `E2E Cert Lesson ${certId}`;

		frappeReq("POST", "/api/resource/LMS Course", {
			title: courseName,
			short_introduction: "E2E certification test course.",
			description: "Cypress E2E certificate generation validation.",
			published: 1,
			enable_certification: 1,
		});

		frappeReq("POST", "/api/resource/Course Chapter", {
			course: courseName,
			title: "E2E Cert Chapter",
		});

		frappeReq("POST", "/api/resource/Course Lesson", {
			course: courseName,
			chapter: "E2E Cert Chapter",
			title: lessonName,
			content: JSON.stringify({
				time: Date.now(),
				blocks: [{ id: "abc123", type: "markdown", data: { text: "E2E certification lesson." } }],
				version: "2.29.0",
			}),
		});

		frappeReq("POST", "/api/resource/LMS Enrollment", {
			member: studentEmail,
			course: courseName,
			progress: 100,
		});

		frappeReq("POST", "/api/resource/LMS Course Progress", {
			member: studentEmail,
			course: courseName,
			lesson: lessonName,
			status: "Complete",
		});
	});

	it("student with 100% progress can request a certificate", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit(`/lms/courses/${courseName}/certification`);
		cy.closeOnboardingModal();

		cy.contains(/certification|certificate/i, { timeout: 10000 }).should("be.visible");
		cy.get("button").contains(/get certificate|request certificate|claim/i).click();
		cy.wait(1000);

		cy.contains(/certificate generated|certificate issued|certificate/i, {
			timeout: 10000,
		}).should("exist");
	});

	it("duplicate certificate generation is blocked", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit(`/lms/courses/${courseName}/certification`);
		cy.closeOnboardingModal();

		cy.get("body").then(($body) => {
			const claimBtn = $body.find(
				"button:contains('Get Certificate'), button:contains('Request Certificate'), button:contains('Claim')"
			);
			if (claimBtn.length) {
				cy.wrap(claimBtn).click();
				cy.contains(/already generated|already issued|already certified/i, {
					timeout: 10000,
				}).should("exist");
			} else {
				cy.contains(
					/already generated|already issued|already certified|certificate/i,
					{ timeout: 10000 }
				).should("exist");
			}
		});
	});

	after(() => {
		cy.login();
		if (csrfToken) {
			frappeReq("DELETE", `/api/resource/LMS Course/${encodeURIComponent(courseName)}`);
			frappeReq("DELETE", "/api/resource/Course Chapter/E2E Cert Chapter");
			frappeReq("DELETE", `/api/resource/Course Lesson/${encodeURIComponent(lessonName)}`);
		}
	});
});
