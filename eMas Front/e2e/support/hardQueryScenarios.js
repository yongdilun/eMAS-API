export const HARD_QUERY_FORBIDDEN_RUNTIME_PATTERNS = Object.freeze([
  { label: 'planner recursion limit', pattern: /recursion limit|GraphRecursionError/i },
  { label: 'planner loop diagnostic', pattern: /\b(?:tool|planner|decision)\s+loop\b/i },
  { label: 'stale completion marker', pattern: /stale completion|non_terminal_snapshot/i },
  { label: 'raw assistant success markdown', pattern: /\*\*Success\*\*/i },
  { label: 'raw assistant done_all marker', pattern: /(?:^|\s)done_all(?:\s|$)/i },
  { label: 'fake success text', pattern: /fake success|pretend(?:ed)? success/i },
])

export const hardQueryScenarios = Object.freeze([
  {
    id: 'HQ-01',
    tags: ['hard query', 'status-only', 'response_document'],
    prompt: 'Show status for machine M-CNC-01 only. Do not show other machine details.',
    expected: {
      sessionStatus: 'COMPLETED',
      responseState: 'completed',
      approvalCount: 0,
      maxStepCount: 3,
      stepSequence: [
        {
          toolName: 'get__machines_{id}',
          args: {
            id: 'M-CNC-01',
            fields: ['machine_id', 'status'],
          },
        },
      ],
      toolNames: ['get__machines_{id}'],
      noMutation: true,
      responseDocument: {
        contracts: ['entity_status_v1'],
        blockTypes: ['status_result'],
        blocks: [
          {
            type: 'status_result',
            contract: 'entity_status_v1',
            readScope: 'status_only',
            requestedFields: ['machine_id', 'status'],
            displayMode: 'compact_status_card',
            entityType: 'machine',
            entityCount: 1,
          },
        ],
      },
      visibleSemanticBlocks: [
        {
          type: 'status_result',
          contract: 'entity_status_v1',
          readScope: 'status_only',
          requestedFields: ['machine_id', 'status'],
          displayMode: 'compact_status_card',
          entityType: 'machine',
          statusFieldKeys: ['machine_id', 'status'],
          forbiddenStatusFieldKeys: [
            'machine_name',
            'machine_type',
            'location',
            'capacity_per_hour',
            'last_maintenance',
            'maintenance_interval',
          ],
        },
      ],
      forbiddenVisibleText: [
        { label: 'machine name label', pattern: /\bMachine name\b/i },
        { label: 'machine type label', pattern: /\bMachine type\b/i },
        { label: 'location label', pattern: /\bLocation\b/i },
        { label: 'capacity label', pattern: /\bCapacity per hour\b/i },
        { label: 'last maintenance label', pattern: /\bLast maintenance\b/i },
        { label: 'maintenance interval label', pattern: /\bMaintenance interval\b/i },
        { label: 'seeded machine name value', pattern: /\bCNC Mill 01\b/i },
        { label: 'seeded floor/location value', pattern: /\bFloor\s+[A-Z]\b/i },
      ],
      forbiddenBackendText: [
        { label: 'response document machine name label', pattern: /\bMachine name\b/i },
        { label: 'response document machine type label', pattern: /\bMachine type\b/i },
        { label: 'response document location label', pattern: /\bLocation\b/i },
        { label: 'response document capacity label', pattern: /\bCapacity per hour\b/i },
        { label: 'response document last maintenance label', pattern: /\bLast maintenance\b/i },
        { label: 'response document maintenance interval label', pattern: /\bMaintenance interval\b/i },
      ],
    },
  },
  {
    id: 'HQ-05',
    tags: ['hard query', 'job-list', 'response_document'],
    prompt: 'List low priority jobs, only job id and deadline, sorted by deadline ascending, limit 3.',
    expected: {
      sessionStatus: 'COMPLETED',
      responseState: 'completed',
      approvalCount: 0,
      maxStepCount: 3,
      stepSequence: [
        {
          toolName: 'get__jobs',
          args: {
            priority: 'low',
            fields: ['job_id', 'deadline'],
            sort_by: 'deadline',
            sort_dir: 'asc',
            limit: 3,
          },
        },
      ],
      toolNames: ['get__jobs'],
      noMutation: true,
      responseDocument: {
        blockTypes: ['result_table'],
        blocks: [
          {
            type: 'result_table',
            readScope: 'records',
            requestedFields: ['job_id', 'deadline'],
            displayMode: 'collection_table',
            entityType: 'job',
            maxRows: 3,
            tableColumnKeys: ['job_id', 'deadline'],
          },
        ],
      },
      visibleSemanticBlocks: [
        {
          type: 'result_table',
          readScope: 'records',
          requestedFields: ['job_id', 'deadline'],
          displayMode: 'collection_table',
          entityType: 'job',
          maxRows: 3,
          tableColumnKeys: ['job_id', 'deadline'],
          forbiddenTableColumnKeys: ['priority', 'product_id', 'status', 'row_id', 'operation_id', 'tool_name'],
        },
      ],
      forbiddenVisibleText: [
        { label: 'product column label', pattern: /\bProduct\b/i },
        { label: 'status column label', pattern: /\bStatus\b/i },
      ],
    },
  },
  {
    id: 'HQ-3S-01',
    tags: ['hard query', 'multi-read', 'response_document'],
    prompt: 'Show M-CNC-01 status, then show JOB-SEED-001 status, then list the next 3 low priority jobs sorted by deadline.',
    expected: {
      sessionStatus: 'COMPLETED',
      responseState: 'completed',
      approvalCount: 0,
      minStepCount: 3,
      maxStepCount: 6,
      stepSequence: [
        {
          toolName: 'get__machines_{id}',
          args: {
            id: 'M-CNC-01',
            fields: ['machine_id', 'status'],
          },
        },
        {
          toolName: 'get__jobs_{id}',
          args: {
            id: 'JOB-SEED-001',
            fields: ['job_id', 'status'],
          },
        },
        {
          toolName: 'get__jobs',
          args: {
            priority: 'low',
            sort_by: 'deadline',
            sort_dir: 'asc',
            limit: 3,
          },
        },
      ],
      toolNames: ['get__machines_{id}', 'get__jobs_{id}', 'get__jobs'],
      noMutation: true,
      responseDocument: {
        minReadRunSteps: 3,
        blocks: [
          {
            type: 'result_table',
            maxRows: 5,
          },
        ],
      },
      visibleSemanticBlocks: [
        {
          type: 'result_table',
          maxRows: 5,
        },
      ],
      forbiddenVisibleText: [
        { label: 'approval required after read-only multi-step', pattern: /Approval required/i },
      ],
    },
  },
])

export function hardQueryScenarioById(id) {
  return hardQueryScenarios.find((scenario) => scenario.id === id) || null
}
