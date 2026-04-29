package service

type ProposeScheduleHandler struct{}

func (h *ProposeScheduleHandler) IntentName() string { return "propose_schedule" }
func (h *ProposeScheduleHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if j := ctx.str("job_id"); j != "" {
		return []ExecutableCall{
			{Method: "GET", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/assist", Purpose: "AI assist payload."},
			{Method: "POST", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/proposals", Purpose: "Persist proposal."},
		}, nil
	}
	return nil, nil
}

type ApproveProposalHandler struct{}

func (h *ApproveProposalHandler) IntentName() string { return "approve_proposal" }
func (h *ApproveProposalHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if p := ctx.str("proposal_id"); p != "" {
		return []ExecutableCall{{Method: "POST", Path: ctx.base + "/ai/scheduling/proposals/" + p + "/approve", Purpose: "Approve proposal."}}, nil
	}
	return nil, nil
}

type RejectProposalHandler struct{}

func (h *RejectProposalHandler) IntentName() string { return "reject_proposal" }
func (h *RejectProposalHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if p := ctx.str("proposal_id"); p != "" {
		return []ExecutableCall{{Method: "POST", Path: ctx.base + "/ai/scheduling/proposals/" + p + "/reject", Purpose: "Reject proposal."}}, nil
	}
	return nil, nil
}

type ApplyProposalHandler struct{}

func (h *ApplyProposalHandler) IntentName() string { return "apply_proposal" }
func (h *ApplyProposalHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if p := ctx.str("proposal_id"); p != "" {
		return []ExecutableCall{{Method: "POST", Path: ctx.base + "/ai/scheduling/proposals/" + p + "/apply", Purpose: "Apply proposal."}}, nil
	}
	if j := ctx.str("job_id"); j != "" {
		return []ExecutableCall{{Method: "POST", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/proposals", Purpose: "Generate proposal for job."}}, nil
	}
	return nil, nil
}

type ScheduleAllJobsHandler struct{}

func (h *ScheduleAllJobsHandler) IntentName() string { return "schedule_all_jobs" }
func (h *ScheduleAllJobsHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	return []ExecutableCall{{
		Method: "POST", Path: ctx.base + "/ai/scheduling/batch-proposals",
		Body:    map[string]interface{}{"scope": "all_unscheduled"},
		Purpose: "Batch schedule all unscheduled jobs.",
	}}, nil
}

type ExplainJobHandler struct{}

func (h *ExplainJobHandler) IntentName() string { return "explain_job" }
func (h *ExplainJobHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if j := ctx.str("job_id"); j != "" {
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/explanation", Purpose: "Job reasoning."}}, nil
	}
	return nil, nil
}

type DelayRiskHandler struct{}

func (h *DelayRiskHandler) IntentName() string { return "delay_risk" }
func (h *DelayRiskHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if j := ctx.str("job_id"); j != "" {
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/delay-risk", Purpose: "Delay risk evaluation."}}, nil
	}
	return nil, nil
}

type MachineRankingHandler struct{}

func (h *MachineRankingHandler) IntentName() string { return "machine_ranking" }
func (h *MachineRankingHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if js := ctx.str("job_step_id"); js != "" {
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/ai/scheduling/job-steps/" + js + "/machine-ranking", Purpose: "Machine ranking for job step."}}, nil
	}
	return nil, nil
}

type RescheduleJobHandler struct{}

func (h *RescheduleJobHandler) IntentName() string { return "reschedule" }
func (h *RescheduleJobHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if j := ctx.str("job_id"); j != "" {
		return []ExecutableCall{
			{Method: "GET", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/assist", Purpose: "Review assist before reschedule."},
			{Method: "POST", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/proposals", Purpose: "Generate new proposal for reschedule."},
		}, nil
	}
	return nil, nil
}

type SplitStepHandler struct{}

func (h *SplitStepHandler) IntentName() string { return "split_step" }
func (h *SplitStepHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if js := ctx.str("job_step_id"); js != "" {
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/ai/scheduling/job-steps/" + js + "/split-suggestion", Purpose: "Split suggestion for job step."}}, nil
	}
	return nil, nil
}
