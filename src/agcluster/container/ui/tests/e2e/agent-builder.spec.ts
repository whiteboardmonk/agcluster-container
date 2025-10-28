import { test, expect } from '@playwright/test';

test.describe('Agent Builder Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to builder page
    await page.goto('/builder');
  });

  test('should display agent builder form', async ({ page }) => {
    // Check header
    await expect(page.locator('h1')).toContainText('Agent Configuration Builder');

    // Check all form sections are visible
    await expect(page.getByText('Basic Information')).toBeVisible();
    await expect(page.getByText('Available Tools')).toBeVisible();
    await expect(page.getByText('Permission Mode')).toBeVisible();
    await expect(page.getByText('Resource Limits')).toBeVisible();
    await expect(page.getByText('Maximum Turns')).toBeVisible();

    // Check YAML preview is visible
    await expect(page.getByText('YAML Preview')).toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    // Try to save without filling required fields
    const saveButton = page.getByRole('button', { name: 'Save Configuration' });

    // Button should be disabled when required fields are empty
    await expect(saveButton).toBeDisabled();
  });

  test('should allow filling agent configuration form', async ({ page }) => {
    // Fill Agent ID
    const idInput = page.getByPlaceholder('e.g., my-custom-agent');
    await idInput.fill('test-agent');

    // Fill Agent Name
    const nameInput = page.getByPlaceholder('e.g., My Custom Agent');
    await nameInput.fill('Test Agent');

    // Fill Description
    const descInput = page.getByPlaceholder('Brief description');
    await descInput.fill('A test agent for E2E testing');

    // Fill System Prompt
    const promptInput = page.getByPlaceholder('You are a helpful assistant');
    await promptInput.fill('You are a test agent that helps with testing');

    // Verify save button is now enabled
    const saveButton = page.getByRole('button', { name: 'Save Configuration' });
    await expect(saveButton).toBeEnabled();
  });

  test('should allow selecting tools', async ({ page }) => {
    // Click "Select All" button
    await page.getByRole('button', { name: /select all/i }).click();

    // Verify tool count updated
    await expect(page.locator('text=/11 of 11 tools selected/')).toBeVisible();

    // Click "Clear All" button
    await page.getByRole('button', { name: /clear all/i }).click();

    // Verify tool count updated
    await expect(page.locator('text=/0 of 11 tools selected/')).toBeVisible();

    // Select specific tools by finding checkbox within the label containing the tool name
    await page.locator('label', { hasText: 'Bash' }).locator('input[type="checkbox"]').check();
    await page.locator('label', { hasText: 'Read' }).locator('input[type="checkbox"]').check();

    // Verify tool count
    await expect(page.locator('text=/2 of 11 tools selected/')).toBeVisible();
  });

  test('should generate YAML preview in real-time', async ({ page }) => {
    // Fill form fields
    await page.getByPlaceholder('e.g., my-custom-agent').fill('preview-test');
    await page.getByPlaceholder('e.g., My Custom Agent').fill('Preview Test');

    // Check YAML preview updates
    const yamlPreview = page.locator('pre').first();
    await expect(yamlPreview).toContainText('id: preview-test');
    await expect(yamlPreview).toContainText('name: Preview Test');
  });

  test('should allow adjusting resource limits', async ({ page }) => {
    // Adjust CPU quota
    const cpuInput = page.getByLabel('CPU Quota').locator('input[type="number"]');
    await cpuInput.fill('300000');

    // Verify CPU display shows correct value
    await expect(page.getByText('(3.0 CPUs)')).toBeVisible();

    // Change memory limit
    const memorySelect = page.getByLabel('Memory Limit');
    await memorySelect.selectOption('8g');

    // Change storage limit
    const storageSelect = page.getByLabel('Storage Limit');
    await storageSelect.selectOption('20g');

    // Verify YAML reflects changes
    const yamlPreview = page.locator('pre').first();
    await expect(yamlPreview).toContainText('cpu_quota: 300000');
    await expect(yamlPreview).toContainText('memory_limit: 8g');
    await expect(yamlPreview).toContainText('storage_limit: 20g');
  });

  test('should allow changing permission mode', async ({ page }) => {
    const permissionSelect = page.getByLabel('Permission Mode');

    // Test all permission modes
    await permissionSelect.selectOption('confirmEdits');
    const yamlPreview = page.locator('pre').first();
    await expect(yamlPreview).toContainText('permission_mode: confirmEdits');

    await permissionSelect.selectOption('rejectEdits');
    await expect(yamlPreview).toContainText('permission_mode: rejectEdits');

    await permissionSelect.selectOption('acceptEdits');
    await expect(yamlPreview).toContainText('permission_mode: acceptEdits');
  });

  test('should allow downloading YAML configuration', async ({ page }) => {
    // Fill required fields
    await page.getByPlaceholder('e.g., my-custom-agent').fill('download-test');
    await page.getByPlaceholder('e.g., My Custom Agent').fill('Download Test');

    // Click download button
    const downloadPromise = page.waitForEvent('download');
    await page.getByTitle('Download YAML').click();
    const download = await downloadPromise;

    // Verify download filename
    expect(download.suggestedFilename()).toBe('download-test-config.yaml');
  });

  test('should allow copying YAML to clipboard', async ({ page }) => {
    // Grant clipboard permissions
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);

    // Fill form
    await page.getByPlaceholder('e.g., my-custom-agent').fill('copy-test');

    // Click copy button
    await page.getByTitle('Copy YAML').click();

    // Wait for alert
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('copied to clipboard');
      await dialog.accept();
    });
  });

  test('should open load config modal', async ({ page }) => {
    // Click Load Config button
    await page.getByRole('button', { name: 'Load Config' }).click();

    // Verify modal appears
    await expect(page.getByText('Load Configuration')).toBeVisible();
    await expect(page.getByText('Select a configuration to load')).toBeVisible();

    // Close modal
    await page.getByTitle('Close').click();
    await expect(page.getByText('Load Configuration')).not.toBeVisible();
  });

  test('should open test agent modal', async ({ page }) => {
    // Fill required fields first
    await page.getByPlaceholder('e.g., my-custom-agent').fill('test-modal');
    await page.getByPlaceholder('e.g., My Custom Agent').fill('Test Modal');

    // Click Test Agent button
    await page.getByRole('button', { name: 'Test Agent' }).click();

    // Verify modal appears
    await expect(page.getByText('Test Agent: Test Modal')).toBeVisible();
    await expect(page.getByPlaceholder('sk-ant-...')).toBeVisible();

    // Close modal
    await page.locator('button').filter({ hasText: '×' }).click();
    await expect(page.getByText('Test Agent: Test Modal')).not.toBeVisible();
  });

  test('should navigate back to dashboard', async ({ page }) => {
    // Click Back to Dashboard button
    await page.getByRole('button', { name: 'Back to Dashboard' }).click();

    // Verify navigation to home page
    await expect(page).toHaveURL('/');
    await expect(page.locator('h1')).toContainText('AgCluster');
  });

  test('should handle form validation correctly', async ({ page }) => {
    // Fill only Agent ID
    await page.getByPlaceholder('e.g., my-custom-agent').fill('validation-test');

    // Test Agent and Save buttons should still be disabled
    await expect(page.getByRole('button', { name: 'Test Agent' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Save Configuration' })).toBeDisabled();

    // Fill Agent Name
    await page.getByPlaceholder('e.g., My Custom Agent').fill('Validation Test');

    // Buttons should now be enabled
    await expect(page.getByRole('button', { name: 'Test Agent' })).toBeEnabled();
    await expect(page.getByRole('button', { name: 'Save Configuration' })).toBeEnabled();
  });

  test('should update max turns setting', async ({ page }) => {
    // Find max turns input
    const maxTurnsInput = page.getByLabel('Maximum Turns');

    // Update value
    await maxTurnsInput.fill('200');

    // Verify YAML reflects change
    const yamlPreview = page.locator('pre').first();
    await expect(yamlPreview).toContainText('max_turns: 200');
  });

  test('should show all tool categories', async ({ page }) => {
    // Verify all categories are present
    await expect(page.getByText('System')).toBeVisible();
    await expect(page.getByText('Files')).toBeVisible();
    await expect(page.getByText('Search')).toBeVisible();
    await expect(page.getByText('Web')).toBeVisible();
    await expect(page.getByText('Multi-Agent')).toBeVisible();
    await expect(page.getByText('Planning')).toBeVisible();
    await expect(page.getByText('Data')).toBeVisible();
  });

  test('should validate agent ID pattern', async ({ page }) => {
    const idInput = page.getByPlaceholder('e.g., my-custom-agent');

    // Try invalid ID with uppercase
    await idInput.fill('INVALID-ID');

    // Check validation message (HTML5 validation)
    const validationMessage = await idInput.evaluate((el: HTMLInputElement) => el.validationMessage);
    expect(validationMessage).toBeTruthy();
  });
});
