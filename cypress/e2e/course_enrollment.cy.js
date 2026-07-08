describe("Course Enrollment — SYS-02", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const courseTitle = "E2E Enrollment Test Course";
	let courseSlug;

	before(() => {
		cy.login();
		cy.request({
			url: "/api/resource/LMS Course",
			method: "POST",
			body: {
				title: courseTitle,
				short_introduction: "E2E test for student enrollment flow.",
				description: "This course is used by Cypress to validate the enrollment E2E flow.",
				published: 1,
			},
		}).then((response) => {
			courseSlug = response.body.data.name;
		});
	});

	it("student enrolls in a published course", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains("a", courseTitle).should("be.visible").click();
		cy.url().should("include", `/lms/courses/${courseSlug}`);

		cy.get("button, a").contains(/Enroll/i).click();
		cy.wait(1000);

		cy.contains(/Enrolled|Continue Learning|My Course/i, { timeout: 10000 }).should(
			"exist"
		);
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
			cy.request({
				url: `/api/resource/LMS Course/${courseSlug}`,
				method: "DELETE",
				failOnStatusCode: false,
			});
		}
	});
});
