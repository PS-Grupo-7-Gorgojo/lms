import { defineConfig } from "cypress";
import cypressSplit from "cypress-split";

export default defineConfig({
	projectId: "vandxn",
	adminPassword: "admin",
	testUser: "Administrator",
	defaultCommandTimeout: 20000,
	pageLoadTimeout: 15000,
	video: true,
	videoUploadOnPasses: false,
	retries: {
		runMode: 2,
		openMode: 0,
	},
	e2e: {
		baseUrl: "https://gorgojo-lms.duckdns.org/",
		setupNodeEvents(on, config) {
			// Splitting tests only works when Cypress Cloud is not orchestrating parallel runs.
			if (process.env.CYPRESS_CLOUD_PARALLEL !== "1") {
				cypressSplit(on, config);
			}
			return config;
		},
	},
});
