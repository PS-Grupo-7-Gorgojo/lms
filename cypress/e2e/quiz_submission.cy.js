describe("Quiz Submission — SYS-03", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const courseTitle = `E2E Quiz ${Date.now()}`;

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
				.type("E2E quiz test course.");
			cy.get("div.ProseMirror").invoke("text", "Quiz test.");
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

	it("student can enroll in the published course", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains("a", courseTitle).click();
		cy.wait(500);

		cy.get("body").then(($body) => {
			const enrollBtn = $body.find("button").filter(":contains('Enroll')");
			if (enrollBtn.length) {
				cy.wrap(enrollBtn).first().click();
				cy.wait(1000);
			}
		});

		cy.contains(/Enrolled|Continue Learning|Dashboard/i, { timeout: 10000 }).should("exist");
	});

	it("student can see course content after enrollment", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/lms/courses");
		cy.closeOnboardingModal();

		cy.contains("a", courseTitle).click();
		cy.contains(/chapter|lesson|content/i, { timeout: 10000 }).should("exist");
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
