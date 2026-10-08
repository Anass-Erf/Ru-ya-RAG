import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests', timeout: 60000, expect: { timeout: 15000 }, fullyParallel: false, workers: 1,
  reporter: 'list', use: { baseURL: 'http://127.0.0.1:3000', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    { command: '../.venv/bin/python -m uvicorn backend.app.main:app --app-dir .. --host 127.0.0.1 --port 8000 --no-access-log', url: 'http://127.0.0.1:8000/health', reuseExistingServer: false, timeout: 30000, env: { RUYA_ENABLE_GENERATION: 'false', RUYA_ALLOW_EXPERIMENTAL_SEARCH: 'false' } },
    { command: 'npm run start', url: 'http://127.0.0.1:3000', reuseExistingServer: false, timeout: 60000, env: { NEXT_PUBLIC_API_URL: 'http://127.0.0.1:8000' } },
  ],
});
