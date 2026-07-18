describe("Certificate Generation — SYS-06", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const courseTitle = `E2E Cert ${Date.now()}`;

	before(() => {
		cy.login();
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
				.type("E2E certification test.");
			cy.get("div.ProseMirror").invoke("text", "Certificate test.");
			cy.button("Save").click();
		});

		cy.wait(500);
		cy.url().should("include", "/lms/courses/");

		cy.get("header").find("button").contains(/^Publish$/).click();
		cy.contains(/Course published/i, { timeout: 10000 }).should("exist");
	});

	it("published course is visible to students", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains(courseTitle, { timeout: 10000 }).should("be.visible");
	});

	it("student can view the course detail page", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains("a", courseTitle).click();
		cy.url().should("include", "/lms/courses/");
		cy.contains(courseTitle, { timeout: 10000 }).should("be.visible");
	});

	after(() => {
		cy.login();
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.get("body").then(($body) => {
			if ($body.text().includes(courseTitle)) {
				cy.contains("a", courseTitle).click();
				cy.wait(500);

				cy.get("body").then(($detail) => {
					if ($detail.find("button, [role=tab]").filter(":contains('Settings')").length) {
						cy.get("button, [role=tab]").contains("Settings").click();
						cy.wait(500);

						cy.get("header")
							.find('button[aria-haspopup="menu"]')
							.first()
							.click({ force: true });
						cy.get("div[role=menu]").within(() => {
							cy.contains('[role="menuitem"]', "Delete").click();
						});
						cy.get("span").contains("Delete").click();
						cy.wait(500);
					}
				});
			}
		});
	});
});
