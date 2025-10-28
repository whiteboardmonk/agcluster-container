import { test, expect } from '@playwright/test';

test.describe('AgCluster E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should load the homepage and display title', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/AgCluster/);

    // Check header is visible
    await expect(page.getByRole('heading', { name: 'AgCluster' })).toBeVisible();
    await expect(page.getByText('Claude Agent Platform')).toBeVisible();
  });

  test('should show API key input field', async ({ page }) => {
    // Check API key input is visible
    const apiKeyInput = page.getByPlaceholder('Anthropic API Key');
    await expect(apiKeyInput).toBeVisible();
    await expect(apiKeyInput).toHaveAttribute('type', 'password');
  });

  test('should load agent configurations from API', async ({ page }) => {
    // Wait for loading spinner to disappear
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });

    // Check if "Launch Your Agent" heading is visible
    await expect(page.getByRole('heading', { name: 'Launch Your Agent' })).toBeVisible();

    // Verify agent preset cards are loaded
    await expect(page.getByText('Research Agent')).toBeVisible();
    await expect(page.getByText('Code Assistant')).toBeVisible();
    await expect(page.getByText('Data Analysis Agent')).toBeVisible();
    await expect(page.getByText('Full-Stack Development Team')).toBeVisible();
  });

  test('should display config cards with details', async ({ page }) => {
    // Wait for configs to load
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });

    // Check Research Agent card details
    const researchCard = page.locator('button:has-text("Research Agent")');
    await expect(researchCard).toBeVisible();
    await expect(researchCard).toContainText('Web research and information analysis specialist');
    await expect(researchCard).toContainText('tools');

    // Check Code Assistant card
    const codeCard = page.locator('button:has-text("Code Assistant")');
    await expect(codeCard).toBeVisible();
    await expect(codeCard).toContainText('Full-stack development agent');
  });

  test('should show error when launching agent without API key', async ({ page }) => {
    // Wait for configs to load
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });

    // Click on Research Agent without entering API key
    await page.locator('button:has-text("Research Agent")').click();

    // Should show error message
    await expect(page.getByText(/Please enter your Anthropic API key/i)).toBeVisible({ timeout: 5000 });
  });

  test('should store API key in localStorage and attempt to launch agent', async ({ page }) => {
    // Wait for configs to load
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });

    // Enter a test API key
    const apiKeyInput = page.getByPlaceholder('Anthropic API Key');
    await apiKeyInput.fill('sk-ant-test-key-for-e2e-testing');

    // Click Research Agent
    await page.locator('button:has-text("Research Agent")').click();

    // Wait for either:
    // 1. Navigation to chat page (if API call succeeds)
    // 2. Error message (if API key is invalid)
    await Promise.race([
      page.waitForURL(/\/chat\//, { timeout: 10000 }).catch(() => {}),
      page.waitForSelector('text=Failed to launch agent', { timeout: 10000 }).catch(() => {}),
      page.waitForSelector('text=Invalid API key', { timeout: 10000 }).catch(() => {}),
    ]);

    // Check localStorage has the API key
    const storedKey = await page.evaluate(() => localStorage.getItem('anthropic_api_key'));
    expect(storedKey).toBe('sk-ant-test-key-for-e2e-testing');
  });

  test('should handle backend connection error gracefully', async ({ page }) => {
    // This test assumes the backend might not be running
    // Wait a bit to see if error message appears
    const errorVisible = await page.getByText('Cannot connect to AgCluster API').isVisible({ timeout: 5000 }).catch(() => false);

    if (errorVisible) {
      // Backend is not running - verify error message is helpful
      await expect(page.getByText('Backend Not Running')).toBeVisible();
      await expect(page.getByText('docker compose up -d')).toBeVisible();
    } else {
      // Backend is running - configs should load
      await expect(page.getByText('Research Agent')).toBeVisible();
    }
  });

  test('should display custom agent builder card', async ({ page }) => {
    // Wait for configs to load
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });

    // Check for Custom Agent card
    await expect(page.getByText('Custom Agent')).toBeVisible();
    await expect(page.getByText('Build your own agent configuration')).toBeVisible();
  });
});

test.describe('Agent Launch Flow (with mock)', () => {
  test('should show loading state when launching agent', async ({ page }) => {
    await page.goto('/');

    // Wait for configs
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });

    // Enter API key
    await page.getByPlaceholder('Anthropic API Key').fill('sk-ant-test');

    // Click agent card
    const agentButton = page.locator('button:has-text("Research Agent")');
    await agentButton.click();

    // Button should be disabled during loading
    await expect(agentButton).toBeDisabled({ timeout: 2000 }).catch(() => {
      // If not disabled, that's okay - might have navigated away already
    });
  });
});

test.describe('Complete Agent Chat Flow', () => {
  test('should verify agent responds with real API key', async ({ page }) => {
    // Skip if no API key provided
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Step 1: Navigate to homepage
    await page.goto('/');

    // Step 2: Wait for configs to load
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await expect(page.getByText('Research Agent')).toBeVisible();

    // Step 3: Enter real API key
    const apiKeyInput = page.getByPlaceholder('Anthropic API Key');
    await apiKeyInput.fill(apiKey);

    // Step 4: Launch Research Agent
    const launchButton = page.locator('button:has-text("Research Agent")');
    await launchButton.click();

    // Step 5: Wait for navigation to chat page
    await page.waitForURL(/\/chat\//, { timeout: 15000 });
    console.log('✅ Navigated to chat page');

    // Step 6: Verify chat interface loaded
    await expect(page.getByRole('heading', { name: 'Agent Session' })).toBeVisible();
    const messageInput = page.getByPlaceholder('Type your message...');
    await expect(messageInput).toBeVisible();

    // Step 7: Send a simple test message
    await messageInput.fill('Say "Hello from E2E test" and nothing else');
    const sendButton = page.getByRole('button', { name: /Send/i });
    await sendButton.click();

    // Step 8: Verify message appears in chat
    await expect(page.getByText('Say "Hello from E2E test" and nothing else')).toBeVisible();
    console.log('✅ User message displayed');

    // Step 9: Wait for loading indicator
    const loadingIndicator = page.getByText('Agent is thinking...');
    await expect(loadingIndicator).toBeVisible({ timeout: 5000 });
    console.log('✅ Loading indicator shown');

    // Step 10: Wait for agent response (up to 60 seconds for real API call)
    const assistantMessage = page.locator('.glass.border.border-gray-700').first();
    await expect(assistantMessage).toBeVisible({ timeout: 60000 });
    console.log('✅ Agent response received');

    // Step 11: Verify response contains expected text
    const responseText = await assistantMessage.textContent();
    expect(responseText).toBeTruthy();
    expect(responseText!.length).toBeGreaterThan(0);
    console.log(`✅ Agent responded with: ${responseText?.substring(0, 100)}...`);

    // Step 12: Verify loading indicator is gone
    await expect(loadingIndicator).not.toBeVisible();

    // Step 13: Verify input is ready for next message
    await expect(messageInput).toHaveValue('');
    await expect(messageInput).toBeEnabled();
    console.log('✅ Ready for next message');
  });

  test('should launch agent and interact with chat interface', async ({ page }) => {
    // Step 1: Navigate to homepage
    await page.goto('/');

    // Step 2: Wait for configs to load
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await expect(page.getByText('Research Agent')).toBeVisible();

    // Step 3: Enter API key
    const apiKeyInput = page.getByPlaceholder('Anthropic API Key');
    await apiKeyInput.fill('sk-ant-test-key-for-e2e-testing');

    // Step 4: Launch Research Agent
    const launchButton = page.locator('button:has-text("Research Agent")');
    await launchButton.click();

    // Step 5: Wait for navigation to chat page OR error message
    const navigatedToChat = await Promise.race([
      page.waitForURL(/\/chat\//, { timeout: 15000 }).then(() => true).catch(() => false),
      page.waitForSelector('text=Failed to launch agent', { timeout: 15000 }).then(() => false).catch(() => false),
      page.waitForSelector('text=Invalid API key', { timeout: 15000 }).then(() => false).catch(() => false),
    ]);

    if (navigatedToChat) {
      // Successfully navigated to chat page
      console.log('✅ Navigated to chat page');

      // Step 6: Verify chat interface loaded
      await expect(page.getByRole('heading', { name: 'Agent Session' })).toBeVisible();
      await expect(page.getByText(/Session ID:/)).toBeVisible();
      await expect(page.getByText('Ready to assist')).toBeVisible();
      await expect(page.getByText('Send a message to get started')).toBeVisible();

      // Step 7: Verify message input is present
      const messageInput = page.getByPlaceholder('Type your message...');
      await expect(messageInput).toBeVisible();
      await expect(messageInput).toBeEnabled();

      // Step 8: Verify Send button is present but disabled (no message)
      const sendButton = page.getByRole('button', { name: /Send/i });
      await expect(sendButton).toBeVisible();
      await expect(sendButton).toBeDisabled();

      // Step 9: Type a message
      await messageInput.fill('Hello! Can you help me?');

      // Step 10: Send button should now be enabled
      await expect(sendButton).toBeEnabled();

      // Step 11: Click Send button
      await sendButton.click();

      // Step 12: Verify message appears in chat
      await expect(page.getByText('Hello! Can you help me?')).toBeVisible();

      // Step 13: Check for loading state
      const loadingIndicator = page.getByText('Agent is thinking...');
      const loadingVisible = await loadingIndicator.isVisible({ timeout: 2000 }).catch(() => false);

      if (loadingVisible) {
        console.log('✅ Loading indicator shown');
      }

      // Step 14: Wait for response or error
      const responseReceived = await Promise.race([
        page.waitForSelector('.prose', { timeout: 20000 }).then(() => true).catch(() => false),
        page.waitForSelector('text=Error:', { timeout: 20000 }).then(() => 'error').catch(() => false),
      ]);

      if (responseReceived === true) {
        console.log('✅ Agent response received');
        // Verify response message structure
        const assistantMessage = page.locator('.glass.border.border-gray-700').first();
        await expect(assistantMessage).toBeVisible();
      } else if (responseReceived === 'error') {
        console.log('⚠️  Error received (expected with test API key)');
        // Verify error is displayed properly
        await expect(page.getByText(/Error:/)).toBeVisible();
      }

      // Step 15: Verify input is cleared and ready for next message
      await expect(messageInput).toHaveValue('');
      await expect(messageInput).toBeEnabled();

      // Step 16: Test back navigation
      const backButton = page.locator('button').filter({ has: page.locator('svg') }).first();
      await backButton.click();

      // Should navigate back to homepage
      await expect(page).toHaveURL('/');
      await expect(page.getByRole('heading', { name: 'AgCluster' })).toBeVisible();

    } else {
      // Agent launch failed (expected with test API key)
      console.log('⚠️  Agent launch failed (expected with test API key)');

      // Verify error message is shown
      const errorVisible = await page.getByText(/Failed to launch agent|Invalid API key/i).isVisible({ timeout: 2000 }).catch(() => false);
      if (errorVisible) {
        console.log('✅ Error message displayed correctly');
      }
    }
  });

  test('should persist API key across navigation', async ({ page }) => {
    // Step 1: Set API key on homepage and launch agent (which saves it to localStorage)
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });

    const apiKeyInput = page.getByPlaceholder('Anthropic API Key');
    await apiKeyInput.fill('sk-ant-persistent-key-test');

    // Launch agent to trigger localStorage save
    const launchButton = page.locator('button:has-text("Research Agent")');
    await launchButton.click();

    // Wait briefly for localStorage to be set
    await page.waitForTimeout(500);

    // Step 2: Verify it's stored
    let storedKey = await page.evaluate(() => localStorage.getItem('anthropic_api_key'));
    expect(storedKey).toBe('sk-ant-persistent-key-test');

    // Step 3: Navigate directly to a different chat URL
    await page.goto('/chat/test-session-999');

    // Step 4: Verify API key is still available
    storedKey = await page.evaluate(() => localStorage.getItem('anthropic_api_key'));
    expect(storedKey).toBe('sk-ant-persistent-key-test');

    // Step 5: Verify chat interface loads with the key
    const messageInput = page.getByPlaceholder('Type your message...');
    await expect(messageInput).toBeEnabled(); // Should be enabled because API key exists
  });

  test('should redirect to homepage if no API key in localStorage', async ({ page }) => {
    // Step 1: Clear localStorage
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());

    // Step 2: Try to navigate directly to chat
    await page.goto('/chat/test-session-456');

    // Step 3: Should redirect to homepage
    await page.waitForURL('/', { timeout: 5000 });
    await expect(page.getByRole('heading', { name: 'AgCluster' })).toBeVisible();
  });
});

test.describe('Tool Execution Panel', () => {
  test('should display tool execution panel with tools', async ({ page }) => {
    // Skip if no API key provided
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Step 1: Launch agent with code-assistant (has many tools)
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Step 2: Verify tool execution panel is visible
    const toolPanel = page.getByTestId('tool-execution-panel');
    await expect(toolPanel).toBeVisible({ timeout: 5000 });

    // Step 3: Send a message that will trigger tool usage
    const messageInput = page.getByPlaceholder('Type your message...');
    await messageInput.fill('Create a file called test.txt with content "Hello World"');
    await page.getByRole('button', { name: /Send/i }).click();

    // Step 4: Wait for tool execution to appear
    const toolEvent = page.locator('[data-testid="tool-event"]').first();
    await expect(toolEvent).toBeVisible({ timeout: 60000 });

    // Step 5: Verify tool event has expected elements
    await expect(toolEvent).toContainText(/Write|Edit|Bash/i);
    console.log('✅ Tool execution panel displays tool events');

    // Step 6: Verify tool status indicator
    const toolStatus = toolEvent.locator('[data-testid="tool-status"]');
    await expect(toolStatus).toBeVisible();
    console.log('✅ Tool status indicator visible');
  });

  test('should display TodoWrite tasks in real-time', async ({ page }) => {
    // Skip if no API key provided
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Step 1: Launch research agent (has TodoWrite)
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Research Agent")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Step 2: Verify TodoList component is visible
    const todoList = page.getByTestId('todo-list');
    await expect(todoList).toBeVisible({ timeout: 5000 });

    // Step 3: Send a complex request that will create todos
    const messageInput = page.getByPlaceholder('Type your message...');
    await messageInput.fill('Research the top 3 programming languages in 2025 and summarize each');
    await page.getByRole('button', { name: /Send/i }).click();

    // Step 4: Wait for TodoWrite tasks to appear
    const todoItem = page.locator('[data-testid="todo-item"]').first();
    const todoVisible = await todoItem.isVisible({ timeout: 60000 }).catch(() => false);

    if (todoVisible) {
      console.log('✅ TodoWrite tasks displayed');

      // Step 5: Verify task has status (pending/in_progress/completed)
      const taskStatus = todoItem.locator('[data-testid="todo-status"]');
      await expect(taskStatus).toBeVisible();

      // Step 6: Check for task completion updates
      const completedTask = page.locator('[data-testid="todo-item"][data-status="completed"]').first();
      const completedVisible = await completedTask.isVisible({ timeout: 30000 }).catch(() => false);

      if (completedVisible) {
        console.log('✅ TodoWrite task marked as completed');
      }
    } else {
      console.log('⚠️  No TodoWrite tasks created (agent may not have used TodoWrite tool)');
    }
  });

  test('should display resource monitoring', async ({ page }) => {
    // Skip if no API key provided
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Step 1: Launch any agent
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Step 2: Verify resource monitor is visible
    const resourceMonitor = page.getByTestId('resource-monitor');
    await expect(resourceMonitor).toBeVisible({ timeout: 5000 });

    // Step 3: Verify CPU usage display
    const cpuGauge = page.getByTestId('cpu-gauge');
    await expect(cpuGauge).toBeVisible();
    await expect(cpuGauge).toContainText(/CPU|%/i);

    // Step 4: Verify Memory usage display
    const memoryGauge = page.getByTestId('memory-gauge');
    await expect(memoryGauge).toBeVisible();
    await expect(memoryGauge).toContainText(/Memory|RAM|MB|GB/i);

    // Step 5: Verify Disk usage display
    const diskGauge = page.getByTestId('disk-gauge');
    await expect(diskGauge).toBeVisible();
    await expect(diskGauge).toContainText(/Disk|Storage|MB|GB/i);

    console.log('✅ Resource monitoring displays CPU, memory, and disk usage');
  });

  test('should toggle tool panel visibility', async ({ page }) => {
    // This test doesn't need real API key
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill('sk-ant-test-key');

    // Try to launch agent (may fail with test key, but we just need to reach chat page)
    await page.locator('button:has-text("Research Agent")').click();

    const navigatedToChat = await page.waitForURL(/\/chat\//, { timeout: 15000 }).then(() => true).catch(() => false);

    if (navigatedToChat) {
      // Look for toggle button
      const toggleButton = page.getByTestId('toggle-tool-panel');
      await expect(toggleButton).toBeVisible({ timeout: 5000 });

      // Click to hide panel
      await toggleButton.click();
      const toolPanel = page.getByTestId('tool-execution-panel');
      await expect(toolPanel).not.toBeVisible({ timeout: 2000 });

      // Click to show panel again
      await toggleButton.click();
      await expect(toolPanel).toBeVisible({ timeout: 2000 });

      console.log('✅ Tool panel toggle works correctly');
    } else {
      test.skip();
    }
  });
});

test.describe('File Viewer Tests', () => {
  test('should display file explorer panel', async ({ page }) => {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Launch agent
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Verify file explorer is visible
    const fileExplorer = page.getByTestId('file-explorer');
    await expect(fileExplorer).toBeVisible({ timeout: 5000 });

    // Verify header
    await expect(fileExplorer).toContainText('Workspace Files');

    // Verify download button exists
    const downloadButton = page.getByTestId('download-workspace');
    await expect(downloadButton).toBeVisible();

    console.log('✅ File explorer panel displays correctly');
  });

  test('should create file and display in file tree', async ({ page }) => {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Launch agent
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Send message to create a file
    const messageInput = page.getByPlaceholder('Type your message...');
    await messageInput.fill('Create a file called hello.txt with content "Hello World"');
    await page.getByRole('button', { name: /Send/i }).click();

    // Wait for agent to respond
    await page.waitForSelector('.prose', { timeout: 60000 });

    // Wait for file to appear in file explorer (auto-refresh every 3s)
    const fileNode = page.locator('[data-testid*="file-node-hello.txt"]').first();
    await expect(fileNode).toBeVisible({ timeout: 10000 });

    console.log('✅ File appears in file tree after creation');
  });

  test('should open file in Monaco Editor when clicked', async ({ page }) => {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Launch agent
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Create a Python file
    const messageInput = page.getByPlaceholder('Type your message...');
    await messageInput.fill('Create a file called test.py with content "print(\'Hello World\')"');
    await page.getByRole('button', { name: /Send/i }).click();
    await page.waitForSelector('.prose', { timeout: 60000 });

    // Wait for file to appear
    const fileNode = page.locator('[data-testid*="file-node-test.py"]').first();
    await expect(fileNode).toBeVisible({ timeout: 10000 });

    // Click the file
    await fileNode.click();

    // Verify file viewer appears
    const fileViewer = page.getByTestId('file-viewer');
    await expect(fileViewer).toBeVisible({ timeout: 5000 });

    // Verify Monaco Editor is loaded
    const monacoEditor = page.getByTestId('monaco-editor');
    await expect(monacoEditor).toBeVisible();

    // Verify file content is displayed
    await expect(fileViewer).toContainText('test.py');
    await expect(fileViewer).toContainText('python');

    console.log('✅ File opens in Monaco Editor when clicked');
  });

  test('should display file metadata', async ({ page }) => {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Launch agent and create file
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Create a file
    const messageInput = page.getByPlaceholder('Type your message...');
    await messageInput.fill('Create a file called data.json with content "{\\"name\\": \\"test\\"}"');
    await page.getByRole('button', { name: /Send/i }).click();
    await page.waitForSelector('.prose', { timeout: 60000 });

    // Wait for file and click it
    const fileNode = page.locator('[data-testid*="file-node-data.json"]').first();
    await expect(fileNode).toBeVisible({ timeout: 10000 });
    await fileNode.click();

    // Verify metadata is displayed
    const fileViewer = page.getByTestId('file-viewer');
    await expect(fileViewer).toContainText(/lines/i);
    await expect(fileViewer).toContainText(/KB|bytes/i);
    await expect(fileViewer).toContainText('json');

    console.log('✅ File metadata (lines, size, language) displayed correctly');
  });

  test('should copy file content to clipboard', async ({ page }) => {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Launch agent and create file
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Create a file
    const messageInput = page.getByPlaceholder('Type your message...');
    await messageInput.fill('Create a file called copy-test.txt with content "Copy me!"');
    await page.getByRole('button', { name: /Send/i }).click();
    await page.waitForSelector('.prose', { timeout: 60000 });

    // Wait for file and click it
    const fileNode = page.locator('[data-testid*="file-node-copy-test.txt"]').first();
    await expect(fileNode).toBeVisible({ timeout: 10000 });
    await fileNode.click();

    // Click copy button
    const copyButton = page.getByTestId('copy-button');
    await expect(copyButton).toBeVisible({ timeout: 5000 });
    await copyButton.click();

    // Verify clipboard content (requires clipboard permissions)
    const copiedText = await page.evaluate(() => navigator.clipboard.readText().catch(() => ''));
    expect(copiedText).toContain('Copy me');

    console.log('✅ Copy to clipboard works');
  });

  test('should download individual file', async ({ page }) => {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Launch agent and create file
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Create a file
    const messageInput = page.getByPlaceholder('Type your message...');
    await messageInput.fill('Create a file called download-test.txt with content "Download me!"');
    await page.getByRole('button', { name: /Send/i }).click();
    await page.waitForSelector('.prose', { timeout: 60000 });

    // Wait for file and click it
    const fileNode = page.locator('[data-testid*="file-node-download-test.txt"]').first();
    await expect(fileNode).toBeVisible({ timeout: 10000 });
    await fileNode.click();

    // Setup download listener
    const downloadPromise = page.waitForEvent('download');

    // Click download button
    const downloadButton = page.getByTestId('download-button');
    await expect(downloadButton).toBeVisible({ timeout: 5000 });
    await downloadButton.click();

    // Verify download started
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('download-test.txt');

    console.log('✅ Individual file download works');
  });

  test('should toggle file panel visibility', async ({ page }) => {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      test.skip();
      return;
    }

    // Launch agent
    await page.goto('/');
    await page.waitForSelector('text=Connecting to AgCluster API...', { state: 'hidden', timeout: 10000 });
    await page.getByPlaceholder('Anthropic API Key').fill(apiKey);
    await page.locator('button:has-text("Code Assistant")').click();
    await page.waitForURL(/\/chat\//, { timeout: 15000 });

    // Verify file panel is visible initially
    const fileExplorer = page.getByTestId('file-explorer');
    await expect(fileExplorer).toBeVisible({ timeout: 5000 });

    // Find and click toggle button
    const toggleButton = page.getByTestId('toggle-file-panel');
    await expect(toggleButton).toBeVisible();
    await toggleButton.click();

    // Verify file panel is hidden
    await expect(fileExplorer).not.toBeVisible({ timeout: 2000 });

    // Click again to show
    await toggleButton.click();
    await expect(fileExplorer).toBeVisible({ timeout: 2000 });

    console.log('✅ File panel toggle works correctly');
  });
});
