describe("Course Enrollment — SYS-02", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const courseTitle = "E2E Enrollment Test Course";

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
				.type("E2E student enrollment test");
			cy.get("div.ProseMirror").invoke(
				"text",
				"E2E course for student enrollment validation."
			);
			cy.button("Save").click();
		});

		cy.wait(500);
		cy.url().should("include", "/lms/courses/");

		cy.get("header").find("button").contains(/^Publish$/).click();
		cy.contains(/Course published/i, { timeout: 10000 }).should("exist");
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
		cy.contains(courseTitle).should("not.exist");
	});
});
