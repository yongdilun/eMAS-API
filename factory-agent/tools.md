# Available Tools

## post__ai_command
**Description**: Parse a command
**Method**: POST
**Endpoint**: /ai/command
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "debug": {
      "type": "boolean"
    },
    "execute_readonly": {
      "type": "boolean"
    },
    "query": {
      "type": "string"
    }
  },
  "required": [
    "query"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "debug": "body",
    "execute_readonly": "body",
    "query": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "query"
    ],
    "properties": {
      "debug": {
        "type": "boolean"
      },
      "execute_readonly": {
        "type": "boolean"
      },
      "query": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "debug",
    "execute_readonly",
    "query"
  ],
  "x-body-required": [
    "query"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_metrics
**Description**: Metrics
**Method**: GET
**Endpoint**: /ai/metrics
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_apply-replenishment-batch
**Description**: Apply replenishment batch
**Method**: POST
**Endpoint**: /ai/scheduling/apply-replenishment-batch
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "arrivals": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/dto.ReplenishmentArrivalItem"
      }
    },
    "suggestions": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/dto.ReplenishmentArrivalItem"
      }
    }
  },
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "arrivals": "body",
    "suggestions": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "arrivals": {
        "type": "array",
        "items": {
          "$ref": "#/definitions/dto.ReplenishmentArrivalItem"
        }
      },
      "suggestions": {
        "type": "array",
        "items": {
          "$ref": "#/definitions/dto.ReplenishmentArrivalItem"
        }
      }
    }
  },
  "x-body-fields": [
    "arrivals",
    "suggestions"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_batch-proposals
**Description**: Generate batch proposals
**Method**: POST
**Endpoint**: /ai/scheduling/batch-proposals
**Capability Tags**: ["job", "proposal", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "include_inventory_actions": {
      "type": "boolean"
    },
    "job_ids": {
      "description": "explicit job IDs; if empty and Scope set, use scope",
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "order_by": {
      "description": "\"edd\" | \"epo\" | \"fifo\" (default: \"epo\")",
      "type": "string"
    },
    "scope": {
      "description": "\"all_unscheduled\" = all jobs with status planned/scheduled and no active slots",
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "include_inventory_actions": "body",
    "job_ids": "body",
    "order_by": "body",
    "scope": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "include_inventory_actions": {
        "type": "boolean"
      },
      "job_ids": {
        "description": "explicit job IDs; if empty and Scope set, use scope",
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "order_by": {
        "description": "\"edd\" | \"epo\" | \"fifo\" (default: \"epo\")",
        "type": "string"
      },
      "scope": {
        "description": "\"all_unscheduled\" = all jobs with status planned/scheduled and no active slots",
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "include_inventory_actions",
    "job_ids",
    "order_by",
    "scope"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_bottleneck-forecast
**Description**: Bottleneck forecast
**Method**: GET
**Endpoint**: /ai/scheduling/bottleneck-forecast
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "days_ahead": {
      "type": "integer"
    }
  },
  "required": [
    "days_ahead"
  ],
  "x-path-params": [],
  "x-query-params": [
    "days_ahead"
  ],
  "x-param-sources": {
    "days_ahead": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_job-steps_{id}_machine-ranking
**Description**: Machine ranking
**Method**: GET
**Endpoint**: /ai/scheduling/job-steps/{id}/machine-ranking
**Capability Tags**: ["machine", "job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_job-steps_{id}_split-suggestion
**Description**: Split suggestion
**Method**: GET
**Endpoint**: /ai/scheduling/job-steps/{id}/split-suggestion
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_jobs_{id}_apply-proposal
**Description**: Apply a proposal
**Method**: POST
**Endpoint**: /ai/scheduling/jobs/{id}/apply-proposal
**Capability Tags**: ["job", "proposal", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_jobs_{id}_apply-replenishment
**Description**: Apply replenishment
**Method**: POST
**Endpoint**: /ai/scheduling/jobs/{id}/apply-replenishment
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_jobs_{id}_assist
**Description**: Assist a job
**Method**: GET
**Endpoint**: /ai/scheduling/jobs/{id}/assist
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_jobs_{id}_delay-risk
**Description**: Delay risk
**Method**: GET
**Endpoint**: /ai/scheduling/jobs/{id}/delay-risk
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_jobs_{id}_explanation
**Description**: Explanation
**Method**: GET
**Endpoint**: /ai/scheduling/jobs/{id}/explanation
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_jobs_{id}_proposal
**Description**: Generate a proposal
**Method**: GET
**Endpoint**: /ai/scheduling/jobs/{id}/proposal
**Capability Tags**: ["job", "proposal", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_jobs_{id}_proposal
**Description**: Generate a proposal
**Method**: POST
**Endpoint**: /ai/scheduling/jobs/{id}/proposal
**Capability Tags**: ["job", "proposal", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_jobs_{id}_proposals
**Description**: List proposals
**Method**: GET
**Endpoint**: /ai/scheduling/jobs/{id}/proposals
**Capability Tags**: ["job", "proposal", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_jobs_{id}_replenish-and-replan
**Description**: Replenish and replan
**Method**: POST
**Endpoint**: /ai/scheduling/jobs/{id}/replenish-and-replan
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_jobs_{id}_shortage-analysis
**Description**: Shortage analysis
**Method**: GET
**Endpoint**: /ai/scheduling/jobs/{id}/shortage-analysis
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__ai_scheduling_proposals_{id}
**Description**: Get a proposal
**Method**: GET
**Endpoint**: /ai/scheduling/proposals/{id}
**Capability Tags**: ["job", "proposal", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_proposals_{id}_apply
**Description**: Apply a proposal by ID
**Method**: POST
**Endpoint**: /ai/scheduling/proposals/{id}/apply
**Capability Tags**: ["job", "proposal", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_proposals_{id}_approve
**Description**: Approve a proposal
**Method**: POST
**Endpoint**: /ai/scheduling/proposals/{id}/approve
**Capability Tags**: ["job", "proposal", "create", "approve"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_proposals_{id}_reject
**Description**: Reject a proposal
**Method**: POST
**Endpoint**: /ai/scheduling/proposals/{id}/reject
**Capability Tags**: ["job", "proposal", "create", "reject"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_reschedule-all
**Description**: Reschedule all
**Method**: POST
**Endpoint**: /ai/scheduling/reschedule-all
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "dry_run": {
      "description": "if true: preview only, no cancel/delete/persist; returns proposals without side effects",
      "type": "boolean"
    },
    "order_by": {
      "description": "\"edd\" | \"epo\" | \"fifo\" | \"readiness\" (default: \"epo\")",
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "dry_run": "body",
    "order_by": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "dry_run": {
        "description": "if true: preview only, no cancel/delete/persist; returns proposals without side effects",
        "type": "boolean"
      },
      "order_by": {
        "description": "\"edd\" | \"epo\" | \"fifo\" | \"readiness\" (default: \"epo\")",
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "dry_run",
    "order_by"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__ai_scheduling_verify-overlaps
**Description**: Verify overlaps
**Method**: POST
**Endpoint**: /ai/scheduling/verify-overlaps
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "job_ids": {
      "description": "optional when scope=applied; if empty, check all jobs with active slots",
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "proposal_ids": {
      "description": "fetch proposals from DB (scope=proposals)",
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "proposals": {
      "description": "or pass inline (e.g. data.proposals from batch-proposals)",
      "type": "array",
      "items": {
        "$ref": "#/definitions/dto.VerifyOverlapsProposal"
      }
    },
    "scope": {
      "description": "\"proposals\" (default) | \"applied\" - verify proposals vs applied slots",
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "job_ids": "body",
    "proposal_ids": "body",
    "proposals": "body",
    "scope": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "job_ids": {
        "description": "optional when scope=applied; if empty, check all jobs with active slots",
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "proposal_ids": {
        "description": "fetch proposals from DB (scope=proposals)",
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "proposals": {
        "description": "or pass inline (e.g. data.proposals from batch-proposals)",
        "type": "array",
        "items": {
          "$ref": "#/definitions/dto.VerifyOverlapsProposal"
        }
      },
      "scope": {
        "description": "\"proposals\" (default) | \"applied\" - verify proposals vs applied slots",
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "job_ids",
    "proposal_ids",
    "proposals",
    "scope"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__chatbot_approval_pending
**Description**: List pending approvals
**Method**: GET
**Endpoint**: /chatbot/approval/pending
**Capability Tags**: ["approval", "list", "pending"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__chatbot_approval_{id}
**Description**: Get an approval by ID
**Method**: GET
**Endpoint**: /chatbot/approval/{id}
**Capability Tags**: ["approval", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__chatbot_approval_{id}_approve
**Description**: Approve an approval
**Method**: POST
**Endpoint**: /chatbot/approval/{id}/approve
**Capability Tags**: ["approval", "create", "approve"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__chatbot_approval_{id}_reject
**Description**: Reject an approval
**Method**: POST
**Endpoint**: /chatbot/approval/{id}/reject
**Capability Tags**: ["approval", "create", "reject"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__dashboard_alerts
**Description**: Get alerts
**Method**: GET
**Endpoint**: /dashboard/alerts
**Capability Tags**: ["list", "alerts"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "type": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "status",
    "type",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "status": "query",
    "type": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__dashboard_kpis
**Description**: Get KPIs
**Method**: GET
**Endpoint**: /dashboard/kpis
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__formula
**Description**: List all formulas
**Method**: GET
**Endpoint**: /formula
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "q": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "q",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "q": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__formula
**Description**: Create a formula
**Method**: POST
**Endpoint**: /formula
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "formula_id": {
      "type": "string"
    },
    "formula_name": {
      "type": "string"
    },
    "instructions": {
      "type": "string"
    },
    "safety_notes": {
      "type": "string"
    },
    "version": {
      "type": "integer"
    }
  },
  "required": [
    "formula_id",
    "formula_name"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "formula_id": "body",
    "formula_name": "body",
    "instructions": "body",
    "safety_notes": "body",
    "version": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "formula_id",
      "formula_name"
    ],
    "properties": {
      "formula_id": {
        "type": "string"
      },
      "formula_name": {
        "type": "string"
      },
      "instructions": {
        "type": "string"
      },
      "safety_notes": {
        "type": "string"
      },
      "version": {
        "type": "integer"
      }
    }
  },
  "x-body-fields": [
    "formula_id",
    "formula_name",
    "instructions",
    "safety_notes",
    "version"
  ],
  "x-body-required": [
    "formula_id",
    "formula_name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__formula_{id}
**Description**: Get a formula by ID
**Method**: GET
**Endpoint**: /formula/{id}
**Capability Tags**: ["lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__formula_{id}
**Description**: Delete a formula
**Method**: DELETE
**Endpoint**: /formula/{id}
**Capability Tags**: ["delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__formula_{id}_ingredients
**Description**: List ingredients for a formula
**Method**: GET
**Endpoint**: /formula/{id}/ingredients
**Capability Tags**: ["lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__formula_{id}_ingredients
**Description**: Add an ingredient to a formula
**Method**: POST
**Endpoint**: /formula/{id}/ingredients
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "material_id": {
      "description": "required if product_id not set",
      "type": "string"
    },
    "percentage": {
      "type": "number"
    },
    "product_id": {
      "description": "required if material_id not set (sub-product)",
      "type": "string"
    },
    "quantity": {
      "description": "backward compat, maps to quantity_per_unit",
      "type": "number"
    },
    "quantity_per_unit": {
      "description": "required; qty per 1 unit of parent",
      "type": "number"
    },
    "scrap_rate": {
      "description": "0-1",
      "type": "number"
    },
    "unit": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "material_id": "body",
    "percentage": "body",
    "product_id": "body",
    "quantity": "body",
    "quantity_per_unit": "body",
    "scrap_rate": "body",
    "unit": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "material_id": {
        "description": "required if product_id not set",
        "type": "string"
      },
      "percentage": {
        "type": "number"
      },
      "product_id": {
        "description": "required if material_id not set (sub-product)",
        "type": "string"
      },
      "quantity": {
        "description": "backward compat, maps to quantity_per_unit",
        "type": "number"
      },
      "quantity_per_unit": {
        "description": "required; qty per 1 unit of parent",
        "type": "number"
      },
      "scrap_rate": {
        "description": "0-1",
        "type": "number"
      },
      "unit": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "material_id",
    "percentage",
    "product_id",
    "quantity",
    "quantity_per_unit",
    "scrap_rate",
    "unit"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__inventory_consume
**Description**: Consume a material
**Method**: POST
**Endpoint**: /inventory/consume
**Capability Tags**: ["inventory", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "material_id": {
      "type": "string"
    },
    "quantity": {
      "type": "number"
    },
    "reference_job_id": {
      "type": "string"
    },
    "slot_id": {
      "type": "string"
    }
  },
  "required": [
    "material_id",
    "quantity"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "material_id": "body",
    "quantity": "body",
    "reference_job_id": "body",
    "slot_id": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "material_id",
      "quantity"
    ],
    "properties": {
      "material_id": {
        "type": "string"
      },
      "quantity": {
        "type": "number"
      },
      "reference_job_id": {
        "type": "string"
      },
      "slot_id": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "material_id",
    "quantity",
    "reference_job_id",
    "slot_id"
  ],
  "x-body-required": [
    "material_id",
    "quantity"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__inventory_expected-arrivals
**Description**: List expected arrivals
**Method**: GET
**Endpoint**: /inventory/expected-arrivals
**Capability Tags**: ["inventory", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__inventory_expected-arrivals
**Description**: Schedule an expected arrival
**Method**: POST
**Endpoint**: /inventory/expected-arrivals
**Capability Tags**: ["job", "inventory", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "expected_arrive_at": {
      "type": "string"
    },
    "material_id": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    },
    "quantity": {
      "type": "number"
    }
  },
  "required": [
    "expected_arrive_at",
    "material_id",
    "quantity"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "expected_arrive_at": "body",
    "material_id": "body",
    "notes": "body",
    "quantity": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "expected_arrive_at",
      "material_id",
      "quantity"
    ],
    "properties": {
      "expected_arrive_at": {
        "type": "string"
      },
      "material_id": {
        "type": "string"
      },
      "notes": {
        "type": "string"
      },
      "quantity": {
        "type": "number"
      }
    }
  },
  "x-body-fields": [
    "expected_arrive_at",
    "material_id",
    "notes",
    "quantity"
  ],
  "x-body-required": [
    "expected_arrive_at",
    "material_id",
    "quantity"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__inventory_materials
**Description**: List materials
**Method**: GET
**Endpoint**: /inventory/materials
**Capability Tags**: ["inventory", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__inventory_materials
**Description**: Create a material
**Method**: POST
**Endpoint**: /inventory/materials
**Capability Tags**: ["inventory", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "current_stock": {
      "type": "number"
    },
    "material_id": {
      "type": "string"
    },
    "material_name": {
      "type": "string"
    },
    "min_stock": {
      "type": "number"
    },
    "reorder_level": {
      "type": "number"
    },
    "storage_location": {
      "type": "string"
    },
    "unit": {
      "type": "string"
    }
  },
  "required": [
    "material_id",
    "material_name"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "current_stock": "body",
    "material_id": "body",
    "material_name": "body",
    "min_stock": "body",
    "reorder_level": "body",
    "storage_location": "body",
    "unit": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "material_id",
      "material_name"
    ],
    "properties": {
      "current_stock": {
        "type": "number"
      },
      "material_id": {
        "type": "string"
      },
      "material_name": {
        "type": "string"
      },
      "min_stock": {
        "type": "number"
      },
      "reorder_level": {
        "type": "number"
      },
      "storage_location": {
        "type": "string"
      },
      "unit": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "current_stock",
    "material_id",
    "material_name",
    "min_stock",
    "reorder_level",
    "storage_location",
    "unit"
  ],
  "x-body-required": [
    "material_id",
    "material_name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__inventory_materials_{id}
**Description**: Get a material by ID
**Method**: GET
**Endpoint**: /inventory/materials/{id}
**Capability Tags**: ["inventory", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__inventory_product-stock
**Description**: List product inventory
**Method**: GET
**Endpoint**: /inventory/product-stock
**Capability Tags**: ["inventory", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "product_id": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "product_id",
    "status",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "product_id": "query",
    "status": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__inventory_product-stock
**Description**: Create a product inventory
**Method**: POST
**Endpoint**: /inventory/product-stock
**Capability Tags**: ["inventory", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "available_from": {
      "type": "string"
    },
    "product_id": {
      "type": "string"
    },
    "quantity_on_hand": {
      "type": "number",
      "minimum": 0
    },
    "quantity_reserved": {
      "type": "number"
    },
    "status": {
      "type": "string"
    },
    "storage_location": {
      "type": "string"
    }
  },
  "required": [
    "product_id",
    "quantity_on_hand"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "available_from": "body",
    "product_id": "body",
    "quantity_on_hand": "body",
    "quantity_reserved": "body",
    "status": "body",
    "storage_location": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "product_id",
      "quantity_on_hand"
    ],
    "properties": {
      "available_from": {
        "type": "string"
      },
      "product_id": {
        "type": "string"
      },
      "quantity_on_hand": {
        "type": "number",
        "minimum": 0
      },
      "quantity_reserved": {
        "type": "number"
      },
      "status": {
        "type": "string"
      },
      "storage_location": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "available_from",
    "product_id",
    "quantity_on_hand",
    "quantity_reserved",
    "status",
    "storage_location"
  ],
  "x-body-required": [
    "product_id",
    "quantity_on_hand"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__inventory_receive
**Description**: Receive a material
**Method**: POST
**Endpoint**: /inventory/receive
**Capability Tags**: ["inventory", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "material_id": {
      "type": "string"
    },
    "quantity": {
      "type": "number"
    }
  },
  "required": [
    "material_id",
    "quantity"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "material_id": "body",
    "quantity": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "material_id",
      "quantity"
    ],
    "properties": {
      "material_id": {
        "type": "string"
      },
      "quantity": {
        "type": "number"
      }
    }
  },
  "x-body-fields": [
    "material_id",
    "quantity"
  ],
  "x-body-required": [
    "material_id",
    "quantity"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__inventory_reservations
**Description**: Create a reservation
**Method**: POST
**Endpoint**: /inventory/reservations
**Capability Tags**: ["inventory", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "job_id": {
      "type": "string"
    },
    "job_step_id": {
      "type": "string"
    },
    "material_id": {
      "type": "string"
    },
    "needed_at": {
      "type": "string"
    },
    "reserved_qty": {
      "type": "number"
    }
  },
  "required": [
    "material_id",
    "reserved_qty"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "job_id": "body",
    "job_step_id": "body",
    "material_id": "body",
    "needed_at": "body",
    "reserved_qty": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "material_id",
      "reserved_qty"
    ],
    "properties": {
      "job_id": {
        "type": "string"
      },
      "job_step_id": {
        "type": "string"
      },
      "material_id": {
        "type": "string"
      },
      "needed_at": {
        "type": "string"
      },
      "reserved_qty": {
        "type": "number"
      }
    }
  },
  "x-body-fields": [
    "job_id",
    "job_step_id",
    "material_id",
    "needed_at",
    "reserved_qty"
  ],
  "x-body-required": [
    "material_id",
    "reserved_qty"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__job-steps
**Description**: Create job steps from routing
**Method**: POST
**Endpoint**: /job-steps
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "job_id": {
      "type": "string"
    }
  },
  "required": [
    "job_id"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "job_id": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "job_id"
    ],
    "properties": {
      "job_id": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "job_id"
  ],
  "x-body-required": [
    "job_id"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__job-steps_split
**Description**: Split a step
**Method**: POST
**Endpoint**: /job-steps/split
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "job_step_id": {
      "type": "string"
    },
    "splits": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/dto.CreateSlotRequest"
      }
    }
  },
  "required": [
    "job_step_id",
    "splits"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "job_step_id": "body",
    "splits": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "job_step_id",
      "splits"
    ],
    "properties": {
      "job_step_id": {
        "type": "string"
      },
      "splits": {
        "type": "array",
        "items": {
          "$ref": "#/definitions/dto.CreateSlotRequest"
        }
      }
    }
  },
  "x-body-fields": [
    "job_step_id",
    "splits"
  ],
  "x-body-required": [
    "job_step_id",
    "splits"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__job-steps_{id}_slots
**Description**: List slots by job step ID
**Method**: GET
**Endpoint**: /job-steps/{id}/slots
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__jobs
**Description**: List jobs
**Method**: GET
**Endpoint**: /jobs
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "product_id": {
      "type": "string"
    },
    "status": {
      "type": "string"
    },
    "priority": {
      "type": "string"
    },
    "machine_id": {
      "type": "string"
    },
    "start": {
      "type": "string"
    },
    "end": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "product_id",
    "status",
    "priority",
    "machine_id",
    "start",
    "end",
    "sort_by",
    "sort_dir",
    "limit",
    "offset"
  ],
  "x-param-sources": {
    "product_id": "query",
    "status": "query",
    "priority": "query",
    "machine_id": "query",
    "start": "query",
    "end": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__jobs
**Description**: Create a job
**Method**: POST
**Endpoint**: /jobs
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "deadline": {
      "description": "RFC3339",
      "type": "string"
    },
    "notes": {
      "type": "string"
    },
    "priority": {
      "type": "string",
      "enum": [
        "low",
        "medium",
        "high",
        "urgent"
      ]
    },
    "product_id": {
      "type": "string"
    },
    "quantity_total": {
      "type": "integer"
    },
    "slots": {
      "description": "optional split slots",
      "type": "array",
      "items": {
        "$ref": "#/definitions/dto.CreateSlotRequest"
      }
    }
  },
  "required": [
    "product_id",
    "quantity_total"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "deadline": "body",
    "notes": "body",
    "priority": "body",
    "product_id": "body",
    "quantity_total": "body",
    "slots": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "product_id",
      "quantity_total"
    ],
    "properties": {
      "deadline": {
        "description": "RFC3339",
        "type": "string"
      },
      "notes": {
        "type": "string"
      },
      "priority": {
        "type": "string",
        "enum": [
          "low",
          "medium",
          "high",
          "urgent"
        ]
      },
      "product_id": {
        "type": "string"
      },
      "quantity_total": {
        "type": "integer"
      },
      "slots": {
        "description": "optional split slots",
        "type": "array",
        "items": {
          "$ref": "#/definitions/dto.CreateSlotRequest"
        }
      }
    }
  },
  "x-body-fields": [
    "deadline",
    "notes",
    "priority",
    "product_id",
    "quantity_total",
    "slots"
  ],
  "x-body-required": [
    "product_id",
    "quantity_total"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__jobs_{id}
**Description**: Get a job by ID
**Method**: GET
**Endpoint**: /jobs/{id}
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## put__jobs_{id}
**Description**: Update a job
**Method**: PUT
**Endpoint**: /jobs/{id}
**Capability Tags**: ["job", "update"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "deadline": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    },
    "priority": {
      "type": "string",
      "enum": [
        "low",
        "medium",
        "high",
        "urgent"
      ]
    },
    "quantity_total": {
      "type": "integer"
    },
    "status": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "deadline": "body",
    "notes": "body",
    "priority": "body",
    "quantity_total": "body",
    "status": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "deadline": {
        "type": "string"
      },
      "notes": {
        "type": "string"
      },
      "priority": {
        "type": "string",
        "enum": [
          "low",
          "medium",
          "high",
          "urgent"
        ]
      },
      "quantity_total": {
        "type": "integer"
      },
      "status": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "deadline",
    "notes",
    "priority",
    "quantity_total",
    "status"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__jobs_{id}
**Description**: Delete a job
**Method**: DELETE
**Endpoint**: /jobs/{id}
**Capability Tags**: ["job", "delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__jobs_{id}_slots
**Description**: List slots by job ID
**Method**: GET
**Endpoint**: /jobs/{id}/slots
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__machines
**Description**: List all machines
**Method**: GET
**Endpoint**: /machines
**Capability Tags**: ["machine", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "machine_type": {
      "type": "string"
    },
    "location": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "status",
    "machine_type",
    "location",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "status": "query",
    "machine_type": "query",
    "location": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__machines
**Description**: Create a machine
**Method**: POST
**Endpoint**: /machines
**Capability Tags**: ["machine", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "capacity_per_hour": {
      "type": "integer"
    },
    "default_changeover_time": {
      "type": "integer"
    },
    "default_cleaning_time": {
      "type": "integer"
    },
    "default_setup_time": {
      "type": "integer"
    },
    "location": {
      "type": "string"
    },
    "machine_id": {
      "type": "string"
    },
    "machine_name": {
      "type": "string"
    },
    "machine_type": {
      "type": "string"
    },
    "maintenance_interval_days": {
      "type": "integer"
    }
  },
  "required": [
    "machine_id",
    "machine_name",
    "machine_type"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "capacity_per_hour": "body",
    "default_changeover_time": "body",
    "default_cleaning_time": "body",
    "default_setup_time": "body",
    "location": "body",
    "machine_id": "body",
    "machine_name": "body",
    "machine_type": "body",
    "maintenance_interval_days": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "machine_id",
      "machine_name",
      "machine_type"
    ],
    "properties": {
      "capacity_per_hour": {
        "type": "integer"
      },
      "default_changeover_time": {
        "type": "integer"
      },
      "default_cleaning_time": {
        "type": "integer"
      },
      "default_setup_time": {
        "type": "integer"
      },
      "location": {
        "type": "string"
      },
      "machine_id": {
        "type": "string"
      },
      "machine_name": {
        "type": "string"
      },
      "machine_type": {
        "type": "string"
      },
      "maintenance_interval_days": {
        "type": "integer"
      }
    }
  },
  "x-body-fields": [
    "capacity_per_hour",
    "default_changeover_time",
    "default_cleaning_time",
    "default_setup_time",
    "location",
    "machine_id",
    "machine_name",
    "machine_type",
    "maintenance_interval_days"
  ],
  "x-body-required": [
    "machine_id",
    "machine_name",
    "machine_type"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__machines_downtime
**Description**: Record downtime
**Method**: POST
**Endpoint**: /machines/downtime
**Capability Tags**: ["machine", "create", "downtime"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "cause": {
      "type": "string"
    },
    "end_time": {
      "type": "string"
    },
    "job_step_slot_id": {
      "type": "string"
    },
    "machine_id": {
      "type": "string"
    },
    "start_time": {
      "type": "string"
    }
  },
  "required": [
    "machine_id"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "cause": "body",
    "end_time": "body",
    "job_step_slot_id": "body",
    "machine_id": "body",
    "start_time": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "machine_id"
    ],
    "properties": {
      "cause": {
        "type": "string"
      },
      "end_time": {
        "type": "string"
      },
      "job_step_slot_id": {
        "type": "string"
      },
      "machine_id": {
        "type": "string"
      },
      "start_time": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "cause",
    "end_time",
    "job_step_slot_id",
    "machine_id",
    "start_time"
  ],
  "x-body-required": [
    "machine_id"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__machines_maintenance-alerts
**Description**: Get maintenance alerts
**Method**: GET
**Endpoint**: /machines/maintenance-alerts
**Capability Tags**: ["machine", "list", "maintenance", "alerts"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__machines_reroute-recommendations
**Description**: Get reroute recommendations
**Method**: GET
**Endpoint**: /machines/reroute-recommendations
**Capability Tags**: ["machine", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__machines_utilization
**Description**: Get utilization
**Method**: GET
**Endpoint**: /machines/utilization
**Capability Tags**: ["machine", "list", "utilization"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__machines_{id}
**Description**: Get machine by ID
**Method**: GET
**Endpoint**: /machines/{id}
**Capability Tags**: ["machine", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## put__machines_{id}
**Description**: Update a machine
**Method**: PUT
**Endpoint**: /machines/{id}
**Capability Tags**: ["machine", "update"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "capacity_per_hour": {
      "type": "integer"
    },
    "default_changeover_time": {
      "type": "integer"
    },
    "default_cleaning_time": {
      "type": "integer"
    },
    "default_setup_time": {
      "type": "integer"
    },
    "location": {
      "type": "string"
    },
    "machine_name": {
      "type": "string"
    },
    "machine_type": {
      "type": "string"
    },
    "maintenance_interval_days": {
      "type": "integer"
    },
    "status": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "capacity_per_hour": "body",
    "default_changeover_time": "body",
    "default_cleaning_time": "body",
    "default_setup_time": "body",
    "location": "body",
    "machine_name": "body",
    "machine_type": "body",
    "maintenance_interval_days": "body",
    "status": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "capacity_per_hour": {
        "type": "integer"
      },
      "default_changeover_time": {
        "type": "integer"
      },
      "default_cleaning_time": {
        "type": "integer"
      },
      "default_setup_time": {
        "type": "integer"
      },
      "location": {
        "type": "string"
      },
      "machine_name": {
        "type": "string"
      },
      "machine_type": {
        "type": "string"
      },
      "maintenance_interval_days": {
        "type": "integer"
      },
      "status": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "capacity_per_hour",
    "default_changeover_time",
    "default_cleaning_time",
    "default_setup_time",
    "location",
    "machine_name",
    "machine_type",
    "maintenance_interval_days",
    "status"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__machines_{id}_capabilities
**Description**: Assign a capability to a machine
**Method**: POST
**Endpoint**: /machines/{id}/capabilities
**Capability Tags**: ["machine", "create", "capability"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "efficiency_factor": {
      "type": "number"
    },
    "step_id": {
      "type": "string"
    }
  },
  "required": [
    "id",
    "step_id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "efficiency_factor": "body",
    "step_id": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "step_id"
    ],
    "properties": {
      "efficiency_factor": {
        "type": "number"
      },
      "step_id": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "efficiency_factor",
    "step_id"
  ],
  "x-body-required": [
    "step_id"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__maintenance
**Description**: Record maintenance
**Method**: POST
**Endpoint**: /maintenance
**Capability Tags**: ["create", "maintenance"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "description": {
      "type": "string"
    },
    "end_time": {
      "type": "string"
    },
    "machine_id": {
      "type": "string"
    },
    "maintenance_type": {
      "type": "string"
    },
    "start_time": {
      "type": "string"
    },
    "technician": {
      "type": "string"
    }
  },
  "required": [
    "machine_id"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "description": "body",
    "end_time": "body",
    "machine_id": "body",
    "maintenance_type": "body",
    "start_time": "body",
    "technician": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "machine_id"
    ],
    "properties": {
      "description": {
        "type": "string"
      },
      "end_time": {
        "type": "string"
      },
      "machine_id": {
        "type": "string"
      },
      "maintenance_type": {
        "type": "string"
      },
      "start_time": {
        "type": "string"
      },
      "technician": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "description",
    "end_time",
    "machine_id",
    "maintenance_type",
    "start_time",
    "technician"
  ],
  "x-body-required": [
    "machine_id"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__predictive_confidence
**Description**: Confidence
**Method**: GET
**Endpoint**: /predictive/confidence
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__predictive_forecast
**Description**: Forecast
**Method**: GET
**Endpoint**: /predictive/forecast
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__predictive_high-risk-jobs
**Description**: List high-risk jobs
**Method**: GET
**Endpoint**: /predictive/high-risk-jobs
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__predictive_recommendations
**Description**: List recommendations
**Method**: GET
**Endpoint**: /predictive/recommendations
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__process-steps_{step_id}_materials
**Description**: List materials for a step
**Method**: GET
**Endpoint**: /process-steps/{step_id}/materials
**Capability Tags**: ["inventory", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "step_id": {
      "type": "string"
    },
    "role": {
      "type": "string"
    }
  },
  "required": [
    "role",
    "step_id"
  ],
  "x-path-params": [
    "step_id"
  ],
  "x-query-params": [
    "role"
  ],
  "x-param-sources": {
    "step_id": "path",
    "role": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__process-steps_{step_id}_materials
**Description**: Add a material to a step
**Method**: POST
**Endpoint**: /process-steps/{step_id}/materials
**Capability Tags**: ["inventory", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "step_id": {
      "type": "string"
    },
    "material_id": {
      "description": "required if product_id not set",
      "type": "string"
    },
    "product_id": {
      "description": "required if material_id not set",
      "type": "string"
    },
    "quantity_per_unit": {
      "description": "required",
      "type": "number"
    },
    "role": {
      "description": "\"input\" or \"output\"",
      "type": "string"
    },
    "unit": {
      "type": "string"
    }
  },
  "required": [
    "step_id"
  ],
  "x-path-params": [
    "step_id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "step_id": "path",
    "material_id": "body",
    "product_id": "body",
    "quantity_per_unit": "body",
    "role": "body",
    "unit": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "material_id": {
        "description": "required if product_id not set",
        "type": "string"
      },
      "product_id": {
        "description": "required if material_id not set",
        "type": "string"
      },
      "quantity_per_unit": {
        "description": "required",
        "type": "number"
      },
      "role": {
        "description": "\"input\" or \"output\"",
        "type": "string"
      },
      "unit": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "material_id",
    "product_id",
    "quantity_per_unit",
    "role",
    "unit"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__process-steps_{step_id}_materials_{id}
**Description**: Delete a material from a step
**Method**: DELETE
**Endpoint**: /process-steps/{step_id}/materials/{id}
**Capability Tags**: ["inventory", "delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "step_id": {
      "type": "string"
    },
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id",
    "step_id"
  ],
  "x-path-params": [
    "step_id",
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "step_id": "path",
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__processes
**Description**: List processes
**Method**: GET
**Endpoint**: /processes
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "product_id": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "product_id",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "product_id": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__processes
**Description**: Create a process
**Method**: POST
**Endpoint**: /processes
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "description": {
      "type": "string"
    },
    "process_id": {
      "type": "string"
    },
    "process_name": {
      "type": "string"
    },
    "product_id": {
      "type": "string"
    },
    "version": {
      "type": "integer"
    }
  },
  "required": [
    "process_id",
    "process_name",
    "product_id"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "description": "body",
    "process_id": "body",
    "process_name": "body",
    "product_id": "body",
    "version": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "process_id",
      "process_name",
      "product_id"
    ],
    "properties": {
      "description": {
        "type": "string"
      },
      "process_id": {
        "type": "string"
      },
      "process_name": {
        "type": "string"
      },
      "product_id": {
        "type": "string"
      },
      "version": {
        "type": "integer"
      }
    }
  },
  "x-body-fields": [
    "description",
    "process_id",
    "process_name",
    "product_id",
    "version"
  ],
  "x-body-required": [
    "process_id",
    "process_name",
    "product_id"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__processes_product_{id}
**Description**: Get a process by product ID
**Method**: GET
**Endpoint**: /processes/product/{id}
**Capability Tags**: ["lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__processes_{id}
**Description**: Get a process by ID
**Method**: GET
**Endpoint**: /processes/{id}
**Capability Tags**: ["lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__processes_{id}
**Description**: Delete a process
**Method**: DELETE
**Endpoint**: /processes/{id}
**Capability Tags**: ["delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__processes_{id}_steps
**Description**: List steps by process ID
**Method**: GET
**Endpoint**: /processes/{id}/steps
**Capability Tags**: ["lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__processes_{id}_steps
**Description**: Add a step to a process
**Method**: POST
**Endpoint**: /processes/{id}/steps
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "allow_parallel_execution": {
      "type": "boolean"
    },
    "default_changeover_time": {
      "type": "integer"
    },
    "default_cleaning_time": {
      "type": "integer"
    },
    "default_preparation_time": {
      "type": "integer"
    },
    "default_processing_time": {
      "type": "integer"
    },
    "machine_type_required": {
      "type": "string"
    },
    "max_parallel_machines": {
      "type": "integer"
    },
    "min_split_qty": {
      "type": "integer"
    },
    "notes": {
      "type": "string"
    },
    "quality_check_required": {
      "type": "boolean"
    },
    "step_id": {
      "type": "string"
    },
    "step_name": {
      "type": "string"
    },
    "step_sequence": {
      "type": "integer"
    },
    "step_type": {
      "type": "string"
    },
    "transfer_batch_size": {
      "type": "integer"
    }
  },
  "required": [
    "id",
    "step_name"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "allow_parallel_execution": "body",
    "default_changeover_time": "body",
    "default_cleaning_time": "body",
    "default_preparation_time": "body",
    "default_processing_time": "body",
    "machine_type_required": "body",
    "max_parallel_machines": "body",
    "min_split_qty": "body",
    "notes": "body",
    "quality_check_required": "body",
    "step_id": "body",
    "step_name": "body",
    "step_sequence": "body",
    "step_type": "body",
    "transfer_batch_size": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "step_name"
    ],
    "properties": {
      "allow_parallel_execution": {
        "type": "boolean"
      },
      "default_changeover_time": {
        "type": "integer"
      },
      "default_cleaning_time": {
        "type": "integer"
      },
      "default_preparation_time": {
        "type": "integer"
      },
      "default_processing_time": {
        "type": "integer"
      },
      "machine_type_required": {
        "type": "string"
      },
      "max_parallel_machines": {
        "type": "integer"
      },
      "min_split_qty": {
        "type": "integer"
      },
      "notes": {
        "type": "string"
      },
      "quality_check_required": {
        "type": "boolean"
      },
      "step_id": {
        "type": "string"
      },
      "step_name": {
        "type": "string"
      },
      "step_sequence": {
        "type": "integer"
      },
      "step_type": {
        "type": "string"
      },
      "transfer_batch_size": {
        "type": "integer"
      }
    }
  },
  "x-body-fields": [
    "allow_parallel_execution",
    "default_changeover_time",
    "default_cleaning_time",
    "default_preparation_time",
    "default_processing_time",
    "machine_type_required",
    "max_parallel_machines",
    "min_split_qty",
    "notes",
    "quality_check_required",
    "step_id",
    "step_name",
    "step_sequence",
    "step_type",
    "transfer_batch_size"
  ],
  "x-body-required": [
    "step_name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__production-log
**Description**: Log production
**Method**: POST
**Endpoint**: /production-log
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "downtime_minutes": {
      "description": "Gap 7 - downtime during slot for OEE",
      "type": "integer"
    },
    "end_time": {
      "type": "string"
    },
    "operator_notes": {
      "type": "string"
    },
    "quantity_produced": {
      "type": "integer"
    },
    "quantity_scrap": {
      "type": "integer"
    },
    "slot_id": {
      "type": "string"
    },
    "start_time": {
      "type": "string"
    }
  },
  "required": [
    "slot_id"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "downtime_minutes": "body",
    "end_time": "body",
    "operator_notes": "body",
    "quantity_produced": "body",
    "quantity_scrap": "body",
    "slot_id": "body",
    "start_time": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "slot_id"
    ],
    "properties": {
      "downtime_minutes": {
        "description": "Gap 7 - downtime during slot for OEE",
        "type": "integer"
      },
      "end_time": {
        "type": "string"
      },
      "operator_notes": {
        "type": "string"
      },
      "quantity_produced": {
        "type": "integer"
      },
      "quantity_scrap": {
        "type": "integer"
      },
      "slot_id": {
        "type": "string"
      },
      "start_time": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "downtime_minutes",
    "end_time",
    "operator_notes",
    "quantity_produced",
    "quantity_scrap",
    "slot_id",
    "start_time"
  ],
  "x-body-required": [
    "slot_id"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__products
**Description**: List all products
**Method**: GET
**Endpoint**: /products
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string"
    },
    "product_type": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "status",
    "product_type",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "status": "query",
    "product_type": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__products
**Description**: Create a new product
**Method**: POST
**Endpoint**: /products
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "description": {
      "type": "string"
    },
    "formula_id": {
      "type": "string"
    },
    "process_id": {
      "type": "string"
    },
    "product_id": {
      "type": "string"
    },
    "product_name": {
      "type": "string"
    },
    "product_type": {
      "type": "string"
    },
    "unit_of_measure": {
      "type": "string"
    }
  },
  "required": [
    "product_id",
    "product_name"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "description": "body",
    "formula_id": "body",
    "process_id": "body",
    "product_id": "body",
    "product_name": "body",
    "product_type": "body",
    "unit_of_measure": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "product_id",
      "product_name"
    ],
    "properties": {
      "description": {
        "type": "string"
      },
      "formula_id": {
        "type": "string"
      },
      "process_id": {
        "type": "string"
      },
      "product_id": {
        "type": "string"
      },
      "product_name": {
        "type": "string"
      },
      "product_type": {
        "type": "string"
      },
      "unit_of_measure": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "description",
    "formula_id",
    "process_id",
    "product_id",
    "product_name",
    "product_type",
    "unit_of_measure"
  ],
  "x-body-required": [
    "product_id",
    "product_name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__products_{id}
**Description**: Get a product by ID
**Method**: GET
**Endpoint**: /products/{id}
**Capability Tags**: ["lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## put__products_{id}_bom
**Description**: Link a BOM to a product
**Method**: PUT
**Endpoint**: /products/{id}/bom
**Capability Tags**: ["update"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "bom_items": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/dto.BOMItem"
      }
    },
    "formula_id": {
      "type": "string"
    },
    "process_id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "bom_items": "body",
    "formula_id": "body",
    "process_id": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "bom_items": {
        "type": "array",
        "items": {
          "$ref": "#/definitions/dto.BOMItem"
        }
      },
      "formula_id": {
        "type": "string"
      },
      "process_id": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "bom_items",
    "formula_id",
    "process_id"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__products_{id}_scheduling-definition
**Description**: Get a scheduling definition by product ID
**Method**: GET
**Endpoint**: /products/{id}/scheduling-definition
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__quality_inspections
**Description**: Record an inspection
**Method**: POST
**Endpoint**: /quality/inspections
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "defect_count": {
      "type": "integer"
    },
    "inspector_name": {
      "type": "string"
    },
    "job_step_id": {
      "type": "string"
    },
    "notes": {
      "type": "string"
    },
    "result": {
      "description": "pass, fail",
      "type": "string"
    }
  },
  "required": [
    "job_step_id"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "defect_count": "body",
    "inspector_name": "body",
    "job_step_id": "body",
    "notes": "body",
    "result": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "job_step_id"
    ],
    "properties": {
      "defect_count": {
        "type": "integer"
      },
      "inspector_name": {
        "type": "string"
      },
      "job_step_id": {
        "type": "string"
      },
      "notes": {
        "type": "string"
      },
      "result": {
        "description": "pass, fail",
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "defect_count",
    "inspector_name",
    "job_step_id",
    "notes",
    "result"
  ],
  "x-body-required": [
    "job_step_id"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reference_locations
**Description**: List locations
**Method**: GET
**Endpoint**: /reference/locations
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "q": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "q",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "q": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__reference_locations
**Description**: Create a location
**Method**: POST
**Endpoint**: /reference/locations
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "bay": {
      "type": "string"
    },
    "zone": {
      "type": "string"
    }
  },
  "required": [
    "zone"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "bay": "body",
    "zone": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "zone"
    ],
    "properties": {
      "bay": {
        "type": "string"
      },
      "zone": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "bay",
    "zone"
  ],
  "x-body-required": [
    "zone"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__reference_locations_{id}
**Description**: Delete a location
**Method**: DELETE
**Endpoint**: /reference/locations/{id}
**Capability Tags**: ["delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reference_machine-types
**Description**: List machine types
**Method**: GET
**Endpoint**: /reference/machine-types
**Capability Tags**: ["machine", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "q": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "q",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "q": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__reference_machine-types
**Description**: Create a machine type
**Method**: POST
**Endpoint**: /reference/machine-types
**Capability Tags**: ["machine", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "description": {
      "type": "string"
    },
    "name": {
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "description": "body",
    "name": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "name"
    ],
    "properties": {
      "description": {
        "type": "string"
      },
      "name": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "description",
    "name"
  ],
  "x-body-required": [
    "name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## put__reference_machine-types_{id}
**Description**: Update a machine type
**Method**: PUT
**Endpoint**: /reference/machine-types/{id}
**Capability Tags**: ["machine", "update"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "name": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "description": "body",
    "name": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "description": {
        "type": "string"
      },
      "name": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "description",
    "name"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__reference_machine-types_{id}
**Description**: Delete a machine type
**Method**: DELETE
**Endpoint**: /reference/machine-types/{id}
**Capability Tags**: ["machine", "delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reference_product-types
**Description**: List product types
**Method**: GET
**Endpoint**: /reference/product-types
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "q": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "q",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "q": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__reference_product-types
**Description**: Create a product type
**Method**: POST
**Endpoint**: /reference/product-types
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "name": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "name"
    ],
    "properties": {
      "name": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "name"
  ],
  "x-body-required": [
    "name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__reference_product-types_{id}
**Description**: Delete a product type
**Method**: DELETE
**Endpoint**: /reference/product-types/{id}
**Capability Tags**: ["delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__reference_step-types
**Description**: Create a step type
**Method**: POST
**Endpoint**: /reference/step-types
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "default_machine_type": {
      "type": "string"
    },
    "name": {
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "default_machine_type": "body",
    "name": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "name"
    ],
    "properties": {
      "default_machine_type": {
        "type": "string"
      },
      "name": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "default_machine_type",
    "name"
  ],
  "x-body-required": [
    "name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__reference_step-types_{id}
**Description**: Delete a step type
**Method**: DELETE
**Endpoint**: /reference/step-types/{id}
**Capability Tags**: ["delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reference_storage-locations
**Description**: List storage locations
**Method**: GET
**Endpoint**: /reference/storage-locations
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "q": {
      "type": "string"
    },
    "type": {
      "type": "string"
    },
    "sort_by": {
      "type": "string"
    },
    "sort_dir": {
      "type": "string"
    },
    "limit": {
      "type": "integer"
    },
    "offset": {
      "type": "integer"
    },
    "fields": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [
    "q",
    "type",
    "sort_by",
    "sort_dir",
    "limit",
    "offset",
    "fields"
  ],
  "x-param-sources": {
    "q": "query",
    "type": "query",
    "sort_by": "query",
    "sort_dir": "query",
    "limit": "query",
    "offset": "query",
    "fields": "query"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__reference_storage-locations
**Description**: Create a storage location
**Method**: POST
**Endpoint**: /reference/storage-locations
**Capability Tags**: ["create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string"
    },
    "type": {
      "type": "string"
    }
  },
  "required": [
    "name"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "name": "body",
    "type": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "name"
    ],
    "properties": {
      "name": {
        "type": "string"
      },
      "type": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "name",
    "type"
  ],
  "x-body-required": [
    "name"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## delete__reference_storage-locations_{id}
**Description**: Delete a storage location
**Method**: DELETE
**Endpoint**: /reference/storage-locations/{id}
**Capability Tags**: ["delete"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_bottleneck-forecast
**Description**: Bottleneck forecast
**Method**: GET
**Endpoint**: /reports/bottleneck-forecast
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_inventory-trends
**Description**: Inventory trends
**Method**: GET
**Endpoint**: /reports/inventory-trends
**Capability Tags**: ["inventory", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_job-completion
**Description**: Job completion
**Method**: GET
**Endpoint**: /reports/job-completion
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_machine-utilization
**Description**: Machine utilization
**Method**: GET
**Endpoint**: /reports/machine-utilization
**Capability Tags**: ["machine", "list", "utilization"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_maintenance-efficiency
**Description**: Maintenance efficiency
**Method**: GET
**Endpoint**: /reports/maintenance-efficiency
**Capability Tags**: ["list", "maintenance"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_oee-trends
**Description**: OEE trends
**Method**: GET
**Endpoint**: /reports/oee-trends
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_parse-date-range
**Description**: Parse date range
**Method**: GET
**Endpoint**: /reports/parse-date-range
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_production-output-per-slot
**Description**: Production output per slot
**Method**: GET
**Endpoint**: /reports/production-output-per-slot
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__reports_quality-trends
**Description**: Quality trends
**Method**: GET
**Endpoint**: /reports/quality-trends
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_backfill-training-dataset
**Description**: Backfill training dataset
**Method**: GET
**Endpoint**: /scheduling/backfill-training-dataset
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_candidate-machines
**Description**: Candidate machines
**Method**: GET
**Endpoint**: /scheduling/candidate-machines
**Capability Tags**: ["machine", "job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_estimate-job-completion
**Description**: Estimate job completion
**Method**: GET
**Endpoint**: /scheduling/estimate-job-completion
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__scheduling_events
**Description**: Emit scheduling event
**Method**: POST
**Endpoint**: /scheduling/events
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "payload": {
      "type": "string"
    },
    "type": {
      "type": "string"
    }
  },
  "required": [
    "payload",
    "type"
  ],
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "payload": "body",
    "type": "body"
  },
  "x-body-schema": {
    "type": "object",
    "required": [
      "payload",
      "type"
    ],
    "properties": {
      "payload": {
        "type": "string"
      },
      "type": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "payload",
    "type"
  ],
  "x-body-required": [
    "payload",
    "type"
  ]
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_explosion
**Description**: Explode demand
**Method**: GET
**Endpoint**: /scheduling/explosion
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_is-time-before
**Description**: Is time before
**Method**: GET
**Endpoint**: /scheduling/is-time-before
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_is-valid-iso-date
**Description**: Is valid ISO date
**Method**: GET
**Endpoint**: /scheduling/is-valid-iso-date
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_readiness
**Description**: Check readiness
**Method**: GET
**Endpoint**: /scheduling/readiness
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_refresh-work-calendars
**Description**: Refresh work calendars
**Method**: GET
**Endpoint**: /scheduling/refresh-work-calendars
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## put__scheduling_settings
**Description**: Update scheduling settings
**Method**: PUT
**Endpoint**: /scheduling/settings
**Capability Tags**: ["job", "update"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "auto_reschedule_on_event": {
      "type": "boolean"
    },
    "deviation_penalty_weight": {
      "type": "number"
    },
    "lateness_weight": {
      "type": "number"
    },
    "lock_in_window_minutes": {
      "type": "integer"
    },
    "objective": {
      "type": "string"
    },
    "public_holidays": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "setup_weight": {
      "type": "number"
    },
    "slack_weight": {
      "type": "number"
    },
    "split_strategy": {
      "type": "string"
    },
    "work_days": {
      "type": "string"
    },
    "work_end_time": {
      "type": "string"
    },
    "work_start_time": {
      "type": "string"
    }
  },
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {
    "auto_reschedule_on_event": "body",
    "deviation_penalty_weight": "body",
    "lateness_weight": "body",
    "lock_in_window_minutes": "body",
    "objective": "body",
    "public_holidays": "body",
    "setup_weight": "body",
    "slack_weight": "body",
    "split_strategy": "body",
    "work_days": "body",
    "work_end_time": "body",
    "work_start_time": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "auto_reschedule_on_event": {
        "type": "boolean"
      },
      "deviation_penalty_weight": {
        "type": "number"
      },
      "lateness_weight": {
        "type": "number"
      },
      "lock_in_window_minutes": {
        "type": "integer"
      },
      "objective": {
        "type": "string"
      },
      "public_holidays": {
        "type": "array",
        "items": {
          "type": "string"
        }
      },
      "setup_weight": {
        "type": "number"
      },
      "slack_weight": {
        "type": "number"
      },
      "split_strategy": {
        "type": "string"
      },
      "work_days": {
        "type": "string"
      },
      "work_end_time": {
        "type": "string"
      },
      "work_start_time": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "auto_reschedule_on_event",
    "deviation_penalty_weight",
    "lateness_weight",
    "lock_in_window_minutes",
    "objective",
    "public_holidays",
    "setup_weight",
    "slack_weight",
    "split_strategy",
    "work_days",
    "work_end_time",
    "work_start_time"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_solver-preview
**Description**: Solver preview
**Method**: GET
**Endpoint**: /scheduling/solver-preview
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_training-dataset
**Description**: Export training dataset
**Method**: GET
**Endpoint**: /scheduling/training-dataset
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_training-dataset-stats
**Description**: Training dataset stats
**Method**: GET
**Endpoint**: /scheduling/training-dataset-stats
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## post__scheduling_validate-slot
**Description**: Validate slot
**Method**: POST
**Endpoint**: /scheduling/validate-slot
**Capability Tags**: ["job", "create"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__scheduling_validate-work-days
**Description**: Validate work days
**Method**: GET
**Endpoint**: /scheduling/validate-work-days
**Capability Tags**: ["job", "list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__settings_get
**Description**: Get settings
**Method**: GET
**Endpoint**: /settings/get
**Capability Tags**: ["list"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## put__settings_update
**Description**: Update settings
**Method**: PUT
**Endpoint**: /settings/update
**Capability Tags**: ["update"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {},
  "x-path-params": [],
  "x-query-params": [],
  "x-param-sources": {}
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## get__slots_{id}
**Description**: Get a slot by ID
**Method**: GET
**Endpoint**: /slots/{id}
**Capability Tags**: ["job", "lookup"]
**Requires Approval**: false
**Side Effect Level**: NONE
**Read Only**: true
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path"
  }
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
## put__slots_{id}
**Description**: Update a slot
**Method**: PUT
**Endpoint**: /slots/{id}
**Capability Tags**: ["job", "update"]
**Requires Approval**: true
**Side Effect Level**: HIGH
**Read Only**: false
**Input Schema**:
`json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string"
    },
    "actual_end": {
      "type": "string"
    },
    "actual_start": {
      "description": "Production / execution (Gap 2 - Start, Pause, Resume, Complete)",
      "type": "string"
    },
    "allocation_percent": {
      "type": "number"
    },
    "batch_sequence": {
      "type": "integer"
    },
    "is_parallel": {
      "type": "boolean"
    },
    "machine_id": {
      "type": "string"
    },
    "quantity_planned": {
      "type": "integer"
    },
    "scheduled_end": {
      "type": "string"
    },
    "scheduled_start": {
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  },
  "required": [
    "id"
  ],
  "x-path-params": [
    "id"
  ],
  "x-query-params": [],
  "x-param-sources": {
    "id": "path",
    "actual_end": "body",
    "actual_start": "body",
    "allocation_percent": "body",
    "batch_sequence": "body",
    "is_parallel": "body",
    "machine_id": "body",
    "quantity_planned": "body",
    "scheduled_end": "body",
    "scheduled_start": "body",
    "status": "body"
  },
  "x-body-schema": {
    "type": "object",
    "properties": {
      "actual_end": {
        "type": "string"
      },
      "actual_start": {
        "description": "Production / execution (Gap 2 - Start, Pause, Resume, Complete)",
        "type": "string"
      },
      "allocation_percent": {
        "type": "number"
      },
      "batch_sequence": {
        "type": "integer"
      },
      "is_parallel": {
        "type": "boolean"
      },
      "machine_id": {
        "type": "string"
      },
      "quantity_planned": {
        "type": "integer"
      },
      "scheduled_end": {
        "type": "string"
      },
      "scheduled_start": {
        "type": "string"
      },
      "status": {
        "type": "string"
      }
    }
  },
  "x-body-fields": [
    "actual_end",
    "actual_start",
    "allocation_percent",
    "batch_sequence",
    "is_parallel",
    "machine_id",
    "quantity_planned",
    "scheduled_end",
    "scheduled_start",
    "status"
  ],
  "x-body-required": []
}
`
**Output Schema**:
`json
{
  "type": "object"
}
`
---
