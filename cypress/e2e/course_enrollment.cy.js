describe("Course Enrollment — SYS-02", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const courseTitle = "E2E Enrollment Test Course";
	let courseSlug;
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

		frappeReq("POST", "/api/resource/LMS Course", {
			title: courseTitle,
			short_introduction: "E2E test for student enrollment flow.",
			description: "Cypress E2E course enrollment validation.",
			published: 1,
		}).then((response) => {
			if (response.body && response.body.data) {
				courseSlug = response.body.data.name;
			}
		});
	});

	it("student enrolls in a published course", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains("a", courseTitle).should("be.visible").click();

		cy.get("button, a").contains(/Enroll/i).click();
		cy.wait(1000);

		cy.contains(/Enrolled|Continue Learning|My Course/i, { timeout: 10000 }).should("exist");
	});

	it("enrolled course appears on student dashboard", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains(courseTitle).should("be.visible");
	});

	after(() => {
		cy.login();
		if (courseSlug) {
			frappeReq("DELETE", `/api/resource/LMS Course/${courseSlug}`);
		}
	});
});
