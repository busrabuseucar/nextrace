const { defineConfig } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/browser', workers: 1,
  use: { baseURL: 'http://127.0.0.1:8765' },
  webServer: {
    command: 'python backend/server.py 8765',
    url: 'http://127.0.0.1:8765/api/health', reuseExistingServer: false,
    env: { NEXTRACE_DB_PATH: 'test-results/browser.db' }
  }
});
