import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { seededPortPlan } from './fullStackEnv.js'

function releasePortPlan() {
  const seeded = seededPortPlan()
  const base = process.env.PLAYWRIGHT_RELEASE_PORT_BASE ? Number(process.env.PLAYWRIGHT_RELEASE_PORT_BASE) : null
  return {
    goApiPort: Number(process.env.PLAYWRIGHT_RELEASE_GO_API_PORT || (base ? base + 1 : seeded.goApiPort + 100)),
    factoryAgentPort: Number(process.env.PLAYWRIGHT_RELEASE_FACTORY_AGENT_PORT || (base ? base + 2 : seeded.factoryAgentPort + 100)),
    proxyPort: Number(process.env.PLAYWRIGHT_RELEASE_PROXY_PORT || (base ? base + 3 : seeded.vitePort + 100)),
  }
}

export function releaseArtifactDir(repoRoot = path.resolve(process.cwd(), '..')) {
  return path.resolve(
    process.env.PLAYWRIGHT_RELEASE_ARTIFACT_DIR || path.join(repoRoot, 'eMas Front', 'test-results', 'release-stack'),
  )
}

export function releaseRuntimeEnv(repoRoot = path.resolve(process.cwd(), '..')) {
  const ports = releasePortPlan()
  const artifactDir = releaseArtifactDir(repoRoot)
  const dbDir = path.join(artifactDir, 'db')
  fs.mkdirSync(dbDir, { recursive: true })

  const releaseBaseUrl = `http://127.0.0.1:${ports.proxyPort}`
  const directGoApiBaseUrl = `http://127.0.0.1:${ports.goApiPort}/api/v1`
  const directFactoryAgentBaseUrl = `http://127.0.0.1:${ports.factoryAgentPort}`
  const releaseBuildId = process.env.PLAYWRIGHT_RELEASE_BUILD_ID || `playwright-release-${ports.proxyPort}`
  const backendSchemaVersion = process.env.PLAYWRIGHT_RELEASE_BACKEND_SCHEMA_VERSION || 'playwright-seeded-schema-v1'

  return {
    ...ports,
    repoRoot,
    artifactDir,
    releaseBuildId,
    backendSchemaVersion,
    bearerToken: process.env.PLAYWRIGHT_RELEASE_STATIC_BEARER || 'playwright-release-static-bearer',
    releaseBaseUrl,
    releaseFactoryAgentBaseUrl: `${releaseBaseUrl}/agent`,
    releaseGoApiBaseUrl: `${releaseBaseUrl}/api/v1`,
    rollbackBaseUrl: process.env.PLAYWRIGHT_RELEASE_ROLLBACK_BASE_URL || releaseBaseUrl,
    directGoApiBaseUrl,
    directFactoryAgentBaseUrl,
    goApiHealthUrl: `http://127.0.0.1:${ports.goApiPort}/health`,
    directFactoryAgentReadyUrl: `${directFactoryAgentBaseUrl}/ready`,
    releaseFactoryAgentReadyUrl: `${releaseBaseUrl}/agent/ready`,
    openApiUrl: `http://127.0.0.1:${ports.goApiPort}/swagger/doc.json`,
    goDbPath: path.join(dbDir, `emas-release-${ports.goApiPort}.sqlite`),
    factoryAgentDbPath: path.join(dbDir, `factory-agent-release-${ports.factoryAgentPort}.sqlite`),
    fingerprintPath: path.join(artifactDir, 'env-fingerprint.json'),
    proxyLogPath: path.join(artifactDir, 'release-proxy.log'),
    platform: {
      pid: process.pid,
      node: process.version,
      cwd: process.cwd(),
      tmpdir: os.tmpdir(),
    },
    latencyBudgetsMs: {
      chatOpen: Number(process.env.PLAYWRIGHT_RELEASE_CHAT_OPEN_BUDGET_MS || 10_000),
      firstProgress: Number(process.env.PLAYWRIGHT_RELEASE_FIRST_PROGRESS_BUDGET_MS || 20_000),
      finalAnswer: Number(process.env.PLAYWRIGHT_RELEASE_FINAL_ANSWER_BUDGET_MS || 45_000),
      longStream: Number(process.env.PLAYWRIGHT_RELEASE_LONG_STREAM_BUDGET_MS || 60_000),
    },
  }
}
