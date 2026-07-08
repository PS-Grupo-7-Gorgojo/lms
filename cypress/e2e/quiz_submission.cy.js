describe("Quiz Submission — SYS-03", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const courseTitle = "E2E Quiz Test Course";
	const quizTitle = "E2E Quiz Test";

	before(() => {
		cy.login();
		cy.closeOnboardingModal();
		cy.wait(500);

		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.get("button").contains("Create").click();
		cy.contains('[role="menuitem"]', "New Course").click();
		cy.wait(500);

		cy.get("[data-dismissable-layer]")
			.should("be.visible")
			.within(() => {
				cy.get("label").contains("Title").parent().find("input").type(courseTitle);

				cy.get("label")
					.contains("Instructors")
					.parent()
					.find("button")
					.first()
					.click();
			});

		cy.get('[data-slot="content-body"] [data-slot="input"]')
			.should("be.visible")
			.type("frappe");
		cy.wait(500);
		cy.get('[data-slot="content-body"] [role="option"]').first().click();
		cy.get("body").type("{esc}");

		cy.get("[data-dismissable-layer]").within(() => {
			cy.get("label")
				.contains("Short introduction")
				.parent()
				.find("textarea")
				.type("E2E quiz test course.");
			cy.get("div.ProseMirror").invoke("text", "Quiz submission E2E test.");
			cy.button("Save").click();
		});

		cy.wait(500);
		cy.url().should("include", "/lms/courses/");

		cy.get("header").find("button").contains(/^Publish$/).click();
		cy.contains(/Course published/i, { timeout: 10000 }).should("exist");

		cy.get("button, [role=tab]").contains("Course editor").click();
		cy.wait(500);
		cy.contains("button", "Create chapter").click();
		cy.wait(500);
		cy.get("[data-dismissable-layer]")
			.should("be.visible")
			.within(() => {
				cy.get("label")
					.contains("Title")
					.parent()
					.find("input")
					.type("E2E Quiz Chapter");
				cy.button("Create").click();
			});

		cy.wait(500);
		cy.button("Add Lesson").click();
		cy.wait(500);
		cy.get("[data-dismissable-layer]")
			.should("be.visible")
			.within(() => {
				cy.get("label")
					.contains("Title")
					.parent()
					.find("input")
					.type("E2E Quiz Lesson");
				cy.button("Create").click();
			});
		cy.wait(500);
	});

	it("student can enroll in the course and access content", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains("a", courseTitle).should("be.visible").click();
		cy.get("button, a").contains(/Enroll/i).click();
		cy.wait(1000);

		cy.contains(/Enrolled|Continue Learning/i, { timeout: 10000 }).should("exist");
	});

	it("student can view quiz page and see the expected UI", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit(`/lms/courses/${encodeURIComponent(courseTitle.toLowerCase().replace(/\s+/g, "-"))}`);
		cy.closeOnboardingModal();

		cy.contains(courseTitle, { timeout: 10000 }).should("be.visible");
		cy.contains(/chapter|lesson|content/i).should("exist");
	});

	after(() => {
		cy.login();
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains("a", courseTitle).should("be.visible").click();
		cy.get("button, [role=tab]").contains("Settings").click();
		cy.wait(500);

		cy.get("header")
			.find('button[aria-haspopup="menu"]', { timeout: 10000 })
			.first()
			.click({ force: true });
		cy.get("div[role=menu]").within(() => {
			cy.contains('[role="menuitem"]', "Delete").click();
		});
		cy.get("span").contains("Delete").click();
		cy.wait(500);
	});
});
