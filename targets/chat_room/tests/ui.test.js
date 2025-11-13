/**
 * UI Tests for Personal Website
 *
 * These tests verify that the personal website is accessible and displays content correctly.
 * Tests use Playwright for browser automation.
 *
 * Requirements:
 * - Server must be running on http://localhost:3000
 * - Page should be accessible at root (/) and /index.html
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:3000';

test.describe('Personal Website UI Tests', () => {

  test('should access root path and display content', async ({ page }) => {
    // Navigate to the root path
    const response = await page.goto(BASE_URL);

    // Verify the page loaded successfully
    expect(response.status()).toBe(200);

    // Verify page has HTML content (not empty)
    const content = await page.content();
    expect(content.length).toBeGreaterThan(0);

    // Verify page has some visible text content
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('should access /index.html directly', async ({ page }) => {
    // Navigate to /index.html
    const response = await page.goto(`${BASE_URL}/index.html`);

    // Verify the page loaded successfully
    expect(response.status()).toBe(200);

    // Verify page has HTML content
    const content = await page.content();
    expect(content.length).toBeGreaterThan(0);

    // Verify page has some visible text content
    const bodyText = await page.textContent('body');
    expect(bodyText.length).toBeGreaterThan(0);
  });

});
