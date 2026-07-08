describe("Quiz Submission — SYS-03", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";
	const generateId = () => `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

	let quizName, courseTitle, courseSlug;
	let questionNames = [];
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

		const quizId = generateId();
		quizName = `E2E Quiz ${quizId}`;
		courseTitle = `e2e-quiz-course-${quizId}`;

		frappeReq("POST", "/api/resource/LMS Question", {
			question: "E2E Q1: What is 2 + 2?",
			type: "Choices",
			multiple: 0,
			option_1: "4",
			is_correct_1: 1,
			option_2: "3",
			is_correct_2: 0,
			option_3: "5",
			is_correct_3: 0,
			option_4: "6",
			is_correct_4: 0,
		}).then((r) => {
			if (r.body && r.body.data) questionNames.push(r.body.data.name);
		});

		frappeReq("POST", "/api/resource/LMS Question", {
			question: "E2E Q2: What is the capital of France?",
			type: "Choices",
			multiple: 0,
			option_1: "Paris",
			is_correct_1: 1,
			option_2: "London",
			is_correct_2: 0,
			option_3: "Berlin",
			is_correct_3: 0,
			option_4: "Madrid",
			is_correct_4: 0,
		}).then((r) => {
			if (r.body && r.body.data) questionNames.push(r.body.data.name);
		});

		frappeReq("POST", "/api/resource/LMS Question", {
			question: "E2E Q3: Which language runs in a browser?",
			type: "Choices",
			multiple: 0,
			option_1: "JavaScript",
			is_correct_1: 1,
			option_2: "Python",
			is_correct_2: 0,
			option_3: "Java",
			is_correct_3: 0,
			option_4: "C++",
			is_correct_4: 0,
		}).then((r) => {
			if (r.body && r.body.data) questionNames.push(r.body.data.name);
		});

		frappeReq("POST", "/api/resource/LMS Quiz", {
			title: quizName,
			passing_percentage: 70,
			max_attempts: 3,
			questions: questionNames.map((q) => ({ question: q, marks: 5 })),
		});

		frappeReq("POST", "/api/resource/LMS Course", {
			title: courseTitle,
			short_introduction: "E2E quiz test course.",
			description: "Cypress E2E quiz submission validation.",
			published: 1,
			instructors: [{ instructor: "frappe@example.com" }],
		}).then((r) => {
			if (r.body && r.body.data) courseSlug = r.body.data.name;
		});

		frappeReq("POST", "/api/resource/Course Chapter", {
			course: courseSlug,
			title: "E2E Quiz Chapter",
		});

		frappeReq("POST", "/api/resource/Course Lesson", {
			course: courseSlug,
			chapter: "E2E Quiz Chapter",
			title: "E2E Quiz Lesson",
			content: JSON.stringify({
				time: Date.now(),
				blocks: [{ id: "dkLzbW14ds", type: "quiz", data: { quiz: quizName } }],
				version: "2.29.0",
			}),
		});

		frappeReq("POST", "/api/resource/LMS Enrollment", {
			member: studentEmail,
			course: courseSlug,
		});
	});

	it("student can start a quiz and see the questions", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/quizzes/" + encodeURIComponent(quizName));
		cy.closeOnboardingModal();

		cy.contains(quizName).should("be.visible");
		cy.contains(/start/i).click();

		cy.contains("E2E Q1:", { timeout: 10000 }).should("be.visible");
	});

	it("student can submit the quiz and see a score", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/quizzes/" + encodeURIComponent(quizName));
		cy.closeOnboardingModal();

		cy.contains(/start/i).click();
		cy.wait(500);

		cy.get("input[type=radio]").first().click({ force: true });
		cy.get("button").contains(/submit|enviar/i).click({ force: true });
		cy.get("button").contains(/submit|enviar/i).click({ force: true });

		cy.contains(/submission|score|result/i, { timeout: 15000 }).should("exist");
	});

	after(() => {
		cy.login();
		if (csrfToken) {
			frappeReq("DELETE", `/api/resource/LMS Quiz/${encodeURIComponent(quizName)}`);
			frappeReq("DELETE", `/api/resource/LMS Course/${encodeURIComponent(courseSlug)}`);
			frappeReq("DELETE", "/api/resource/Course Chapter/E2E Quiz Chapter");
			frappeReq("DELETE", "/api/resource/Course Lesson/E2E Quiz Lesson");
			questionNames.forEach((q) => frappeReq("DELETE", `/api/resource/LMS Question/${q}`));
		}
	});
});
