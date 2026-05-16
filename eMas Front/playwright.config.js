import { defineConfig, devices } from '@playwright/test'
import { seededRuntimeEnv } from './e2e/support/fullStackEnv.js'
import { releaseRuntimeEnv } from './e2e/support/releaseEnv.js'

const factoryAgentPort = Number(process.env.PLAYWRIGHT_FACTORY_AGENT_PORT || 8015)
const appPort = Number(process.env.PLAYWRIGHT_VITE_PORT || 4175)
const seededEnv = seededRuntimeEnv()
const releaseEnv = releaseRuntimeEnv()
const selectedProjects = process.argv
  .flatMap((arg, index, all) => (arg === '--project' ? [all[index + 1]] : arg.startsWith('--project=') ? [arg.slice('--project='.length)] : []))
  .filter(Boolean)
const selectedSeeded = selectedProjects.some((project) => project === 'chromium-seeded')
const selectedRelease = selectedProjects.some((project) => project === 'chromium-release')
const selectedMocked = selectedProjects.length === 0 || selectedProjects.some((project) => project === 'chromium')
process.env.PLAYWRIGHT_SEEDED_GO_API_PORT = String(seededEnv.goApiPort)
process.env.PLAYWRIGHT_SEEDED_FACTORY_AGENT_PORT = String(seededEnv.factoryAgentPort)
process.env.PLAYWRIGHT_SEEDED_VITE_PORT = String(seededEnv.vitePort)
process.env.PLAYWRIGHT_SEEDED_ARTIFACT_DIR = seededEnv.artifactDir
process.env.PLAYWRIGHT_RELEASE_GO_API_PORT = String(releaseEnv.goApiPort)
process.env.PLAYWRIGHT_RELEASE_FACTORY_AGENT_PORT = String(releaseEnv.factoryAgentPort)
process.env.PLAYWRIGHT_RELEASE_PROXY_PORT = String(releaseEnv.proxyPort)
process.env.PLAYWRIGHT_RELEASE_ARTIFACT_DIR = releaseEnv.artifactDir
process.env.PLAYWRIGHT_RELEASE_BUILD_ID = releaseEnv.releaseBuildId

const webServer = []
if (selectedMocked) {
  webServer.push(
    {
      command: `node e2e/mock-server/factoryAgentMockServer.js --port ${factoryAgentPort}`,
      url: `http://127.0.0.1:${factoryAgentPort}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: `node e2e/support/startViteForPlaywright.js --port ${appPort} --factory-agent-url http://127.0.0.1:${factoryAgentPort}`,
      url: `http://127.0.0.1:${appPort}`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  )
}
if (selectedSeeded) {
  webServer.push({
    command: `node e2e/support/startSeededStackForPlaywright.js`,
    url: seededEnv.viteBaseUrl,
    reuseExistingServer: false,
    timeout: 150_000,
  })
}
if (selectedRelease) {
  webServer.push({
    command: `node e2e/support/startReleaseStackForPlaywright.js`,
    url: releaseEnv.releaseFactoryAgentReadyUrl,
    reuseExistingServer: false,
    timeout: 180_000,
  })
}

export default defineConfig({
  testDir: './e2e/specs',
  timeout: selectedRelease ? 90_000 : selectedSeeded ? 60_000 : 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: true,
  workers: selectedSeeded || selectedRelease || process.env.CI ? 1 : undefined,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${appPort}`,
    trace: process.env.CI ? 'on-first-retry' : 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer,
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      testIgnore: /(full-stack|release)-.*\.spec\.js/,
    },
    {
      name: 'chromium-seeded',
      testMatch: /full-stack-.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: seededEnv.viteBaseUrl,
      },
    },
    {
      name: 'chromium-release',
      testMatch: /release-.*\.spec\.js/,
      use: {
        ...devices['Desktop Chrome'],
        baseURL: releaseEnv.releaseBaseUrl,
        trace: 'on',
        screenshot: 'on',
        video: 'on',
      },
    },
  ],
})
