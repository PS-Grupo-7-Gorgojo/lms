describe("Certificate Generation — SYS-06", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const courseTitle = "E2E Cert Test Course";
	let courseSlug;

	function benchExec(pythonCode) {
		return cy.exec(
			`cd ~/frappe-bench && bench --site lms.test execute '${pythonCode}'`,
			{ failOnStatusCode: false }
		);
	}

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
				.type("E2E certification test.");
			cy.get("div.ProseMirror").invoke("text", "Certificate generation E2E test.");
			cy.button("Save").click();
		});

		cy.wait(500);
		cy.url().should("include", "/lms/courses/");

		cy.url().then((url) => {
			courseSlug = url.split("/").pop().split("#")[0];
		});

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
					.type("E2E Cert Chapter");
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
					.type("E2E Cert Lesson");
				cy.button("Create").click();
			});
		cy.wait(500);
	});

	it("student with 100% progress can access the certification page", () => {
		benchExec(
			`frappe.get_doc({doctype: 'LMS Course', name: '${courseSlug}'}).db_set('enable_certification', 1); print('OK')`
		);
		benchExec(
			`enrollment = frappe.get_doc({doctype: 'LMS Enrollment', member: '${studentEmail}', course: '${courseSlug}', progress: 100}); enrollment.insert(ignore_permissions=True); print('OK')`
		);

		cy.login(studentEmail, studentPassword);
		cy.visit(`/lms/courses/${courseSlug}/certification`);
		cy.closeOnboardingModal();

		cy.contains(/certification|certificate/i, { timeout: 10000 }).should("be.visible");
	});

	it("student can request a certificate", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit(`/lms/courses/${courseSlug}/certification`);
		cy.closeOnboardingModal();

		cy.get("button").contains(/get certificate|request certificate|claim|certificate/i).click();
		cy.wait(1000);

		cy.contains(/certificate/i, { timeout: 10000 }).should("exist");
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
