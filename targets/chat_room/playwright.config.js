/**
 * Playwright Configuration
 *
 * See https://playwright.dev/docs/test-configuration
 */

const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  testMatch: '**/ui.test.js',

  // Maximum time one test can run
  timeout: 30000,

  // Retry on failure
  retries: 0,

  // Run tests in parallel
  workers: 1,

  // Reporter to use
  reporter: 'list',

  use: {
    // Base URL for navigation
    baseURL: 'http://localhost:3000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',
  },

  // Browser projects
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
  ],
});
