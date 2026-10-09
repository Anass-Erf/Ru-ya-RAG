import { defineConfig, devices } from '@playwright/test';
const apiPort = Number(process.env.RUYA_E2E_API_PORT ?? 18000);
const webPort = Number(process.env.RUYA_E2E_WEB_PORT ?? 13000);
for (const port of [apiPort, webPort]) {
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    throw new Error('E2E ports must be integers between 1024 and 65535');
  }
}
const apiUrl = `http://127.0.0.1:${apiPort}`;
const webUrl = `http://127.0.0.1:${webPort}`;
export default defineConfig({
  testDir: './tests',
  timeout: 60000,
  expect: { timeout: 15000 },
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  use: { baseURL: webUrl, trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `../.venv/bin/python -m uvicorn backend.app.main:app --app-dir .. --host 127.0.0.1 --port ${apiPort} --no-access-log`,
      url: `${apiUrl}/health`,
      reuseExistingServer: false,
      timeout: 30000,
      env: {
        RUYA_ENABLE_GENERATION: 'false',
        RUYA_ALLOW_EXPERIMENTAL_SEARCH: 'false',
        RUYA_CORS_ORIGINS: webUrl,
      },
    },
    {
      command: `npm run build && npm run start -- --port ${webPort}`,
      url: webUrl,
      reuseExistingServer: false,
      timeout: 180000,
      env: { NEXT_PUBLIC_API_URL: apiUrl, RUYA_E2E: '1' },
    },
  ],
});
