describe("Quiz Submission — SYS-03", () => {
	const studentEmail = Cypress.config("testUser") || "frappe@example.com";
	const studentPassword = Cypress.config("adminPassword") || "admin";

	let quizName;
	let courseName;
	let questionNames = [];

	const generateId = () => `e2e-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

	before(() => {
		cy.login();
		const quizId = generateId();
		quizName = `E2E Quiz ${quizId}`;
		courseName = `e2e-quiz-course-${quizId}`;

		cy.request({
			url: "/api/resource/LMS Question",
			method: "POST",
			body: {
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
			},
		}).then((r) => questionNames.push(r.body.data.name));

		cy.request({
			url: "/api/resource/LMS Question",
			method: "POST",
			body: {
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
			},
		}).then((r) => questionNames.push(r.body.data.name));

		cy.request({
			url: "/api/resource/LMS Question",
			method: "POST",
			body: {
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
			},
		}).then((r) => questionNames.push(r.body.data.name));

		cy.request({
			url: "/api/resource/LMS Quiz",
			method: "POST",
			body: {
				title: quizName,
				passing_percentage: 70,
				max_attempts: 3,
				questions: questionNames.map((q) => ({
					question: q,
					marks: 5,
				})),
			},
		});

		cy.request({
			url: "/api/resource/LMS Course",
			method: "POST",
			body: {
				title: courseName,
				short_introduction: "E2E quiz test course.",
				description: "Course for Cypress quiz submission test.",
				published: 1,
			},
		});

		cy.request({
			url: "/api/resource/Course Chapter",
			method: "POST",
			body: {
				course: courseName,
				title: "E2E Quiz Chapter",
			},
		});

		cy.request({
			url: "/api/resource/Course Lesson",
			method: "POST",
			body: {
				course: courseName,
				chapter: "E2E Quiz Chapter",
				title: "E2E Quiz Lesson",
				content: JSON.stringify({
					time: Date.now(),
					blocks: [
						{
							id: "dkLzbW14ds",
							type: "quiz",
							data: { quiz: quizName },
						},
					],
					version: "2.29.0",
				}),
			},
		});

		cy.request({
			url: "/api/resource/LMS Enrollment",
			method: "POST",
			failOnStatusCode: false,
			body: {
				member: studentEmail,
				course: courseName,
			},
		});
	});

	it("student can start a quiz and see the questions", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/quizzes/" + encodeURIComponent(quizName));
		cy.closeOnboardingModal();

		cy.contains(quizName).should("be.visible");
		cy.contains(/start/i).click();

		cy.contains("E2E Q1:").should("be.visible");
		cy.contains("E2E Q2:").should("be.visible");
		cy.contains("E2E Q3:").should("be.visible");
	});

	it("student can submit the quiz and see a score", () => {
		cy.login(studentEmail, studentPassword);
		cy.visit("/quizzes/" + encodeURIComponent(quizName));
		cy.closeOnboardingModal();

		cy.contains(/start/i).click();
		cy.wait(500);

		cy.get("input[type=radio]").first().click({ multiple: true, force: true });
		cy.get("button, [role=button]").contains(/submit|enviar/i).click({ force: true });
		cy.contains(/are you sure|cancel/i, { timeout: 5000 });
		cy.get("button").contains(/submit|enviar/i).click({ force: true });

		cy.contains(/submission|score|result/i, { timeout: 15000 }).should("exist");
	});

	after(() => {
		cy.login();
		const deleteDoc = (doctype, name) => {
			if (name) {
				cy.request({
					url: `/api/resource/${doctype}/${encodeURIComponent(name)}`,
					method: "DELETE",
					failOnStatusCode: false,
				});
			}
		};
		deleteDoc("LMS Quiz", quizName);
		deleteDoc("LMS Course", courseName);
		deleteDoc("Course Chapter", "E2E Quiz Chapter");
		deleteDoc("Course Lesson", "E2E Quiz Lesson");
		questionNames.forEach((q) => deleteDoc("LMS Question", q));
		cy.request({
			url: "/api/resource/LMS Enrollment",
			method: "DELETE",
			failOnStatusCode: false,
		});
	});
});
