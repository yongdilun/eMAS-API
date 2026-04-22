package service

import (
	"context"
	"emas/internal/domain"
	"emas/internal/handler/dto"
	"emas/internal/repository"
	"emas/pkg/featureflags"
	"emas/pkg/id"
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"time"
)

// ChatbotService is the phase 0 chatbot foundation:
// - deterministic planner
// - validated tool calls
// - read-only execution only
// - audit + tool snapshot persistence
type ChatbotService struct {
	convRepo ConversationRepository
	msgRepo  *repository.AIChatMessageRepository
	turnRepo TurnAuditRepository
	planner  ChatPlanner
	executor ReadOnlyToolExecutor
	registry ToolRegistry
}

func NewChatbotService(
	convRepo ConversationRepository,
	msgRepo *repository.AIChatMessageRepository,
	turnRepo TurnAuditRepository,
	planner ChatPlanner,
	executor ReadOnlyToolExecutor,
	registry ToolRegistry,
) *ChatbotService {
	return &ChatbotService{
		convRepo: convRepo,
		msgRepo:  msgRepo,
		turnRepo: turnRepo,
		planner:  planner,
		executor: executor,
		registry: registry,
	}
}

func (s *ChatbotService) ListConversations(limit, offset int) ([]domain.AIConversation, error) {
	return s.convRepo.List(limit, offset)
}

func (s *ChatbotService) CreateConversation(title string) (*domain.AIConversation, error) {
	if title == "" {
		title = "New conversation"
	}
	now := time.Now().UTC()
	conv := &domain.AIConversation{
		ID:        id.New(),
		Title:     title,
		CreatedAt: now,
		UpdatedAt: now,
	}
	if err := s.convRepo.Create(conv); err != nil {
		return nil, err
	}
	welcome := &domain.AIChatMessage{
		ID:             id.New(),
		ConversationID: conv.ID,
		Role:           "assistant",
		Content:        "Welcome back. Ask about jobs, machines, inventory, dashboard KPIs, or provide a job ID like JOB-1234.",
		Metadata:       `{"intent":"welcome","message":"Welcome back. Ask about jobs, machines, inventory, dashboard KPIs, or provide a job ID like JOB-1234."}`,
		CreatedAt:      now,
	}
	_ = s.msgRepo.Create(welcome)
	return conv, nil
}

func (s *ChatbotService) GetConversation(conversationID string) (*domain.AIConversation, []domain.AIChatMessage, error) {
	conv, err := s.convRepo.GetByID(conversationID)
	if err != nil {
		return nil, nil, ErrConversationNotFound
	}
	msgs, err := s.msgRepo.ListByConversationID(conversationID)
	if err != nil {
		return nil, nil, err
	}
	sort.Slice(msgs, func(i, j int) bool {
		if msgs[i].CreatedAt.Before(msgs[j].CreatedAt) {
			return true
		}
		if msgs[i].CreatedAt.After(msgs[j].CreatedAt) {
			return false
		}
		return msgs[i].ID < msgs[j].ID
	})
	return conv, msgs, nil
}

func (s *ChatbotService) SendMessage(conversationID, query, requestID string) (*domain.AIChatMessage, *dto.AICommandResponse, error) {
	conv, err := s.convRepo.GetByID(conversationID)
	if err != nil {
		return nil, nil, ErrConversationNotFound
	}
	now := time.Now().UTC()

	userMsg := &domain.AIChatMessage{
		ID:             id.New(),
		ConversationID: conversationID,
		Role:           "user",
		Content:        query,
		CreatedAt:      now,
	}
	if err := s.msgRepo.Create(userMsg); err != nil {
		return nil, nil, err
	}

	history, err := s.msgRepo.ListByConversationID(conversationID)
	if err != nil {
		return nil, nil, err
	}

	plan, err := s.planner.Plan(query, history, s.registry)
	if err != nil {
		return nil, nil, err
	}
	planJSON, _ := json.Marshal(plan)
	selectedToolsJSON, _ := json.Marshal(plan.ToolCalls)

	audit := &domain.ChatbotTurnAudit{
		ID:                id.NewPrefixed("CHATAUD-"),
		ConversationID:    conversationID,
		RequestID:         requestID,
		UserMessageID:     userMsg.ID,
		PlannerName:       s.planner.Name(),
		PlanJSON:          string(planJSON),
		SelectedToolsJSON: string(selectedToolsJSON),
		Status:            "planned",
		CreatedAt:         now,
	}
	if s.turnRepo != nil {
		_ = s.turnRepo.Create(audit)
	}

	var resp *dto.AICommandResponse
	if plan.Ambiguous {
		resp = &dto.AICommandResponse{
			Intent:         plan.Action,
			Action:         plan.Action,
			Entities:       map[string]interface{}{},
			Confidence:     plan.Confidence,
			Ambiguous:      true,
			Clarifications: plan.ClarificationPrompt,
			Message:        "I need a little more specificity before I can use the approved read-only tools.",
			ExecutionMode:  "suggest_only",
			Executed:       false,
			ResultCards: []dto.AIResultCard{{
				Kind:    "clarification_required",
				Title:   "Clarification Required",
				Tone:    "warning",
				Summary: "Clarify what you want to inspect (jobs, machines, inventory, KPIs) or provide an ID.",
				Bullets: plan.ClarificationPrompt,
			}},
		}
		if s.turnRepo != nil {
			audit.Status = "clarification_required"
			_ = s.turnRepo.Update(audit)
		}
	} else {
		timeoutMs := featureflags.ChatbotTurnTimeoutMs()
		ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutMs)*time.Millisecond)
		defer cancel()
		executions, err := s.executor.Execute(ctx, conversationID, audit.ID, plan.ToolCalls)
		if err != nil {
			if s.turnRepo != nil {
				audit.Status = "execution_failed"
				audit.Error = err.Error()
				_ = s.turnRepo.Update(audit)
			}
			return nil, nil, err
		}
		resp = composeChatbotResponse(plan, executions)
		if s.turnRepo != nil {
			audit.Status = "completed"
			_ = s.turnRepo.Update(audit)
		}
	}

	metaJSON, _ := json.Marshal(resp)
	assistantMsg := &domain.AIChatMessage{
		ID:             id.New(),
		ConversationID: conversationID,
		Role:           "assistant",
		Content:        resp.Message,
		Metadata:       string(metaJSON),
		CreatedAt:      time.Now().UTC(),
	}
	if err := s.msgRepo.Create(assistantMsg); err != nil {
		return nil, nil, err
	}
	if s.turnRepo != nil {
		audit.AssistantMessageID = assistantMsg.ID
		_ = s.turnRepo.Update(audit)
	}

	conv.UpdatedAt = time.Now().UTC()
	if conv.Title == "New conversation" {
		title := strings.TrimSpace(query)
		if len(title) > 50 {
			title = title[:47] + "..."
		}
		if title != "" {
			conv.Title = title
		}
	}
	_ = s.convRepo.Update(conv)

	return assistantMsg, resp, nil
}

func composeChatbotResponse(plan *ChatPlan, executions []ChatToolExecutionResult) *dto.AICommandResponse {
	resp := &dto.AICommandResponse{
		Intent:        plan.Action,
		Action:        plan.Action,
		Entities:      map[string]interface{}{},
		Confidence:    plan.Confidence,
		Ambiguous:     plan.Ambiguous,
		Message:       plan.PlanExplanation,
		ExecutionMode: "executed_readonly",
		Executed:      false,
	}

	insights := map[string]interface{}{}
	for _, execution := range executions {
		insights[execution.Tool.Name] = execution.Output
		resp.SuggestedCalls = append(resp.SuggestedCalls, execution.SuggestedCall)
		resp.ExecutedCalls = append(resp.ExecutedCalls, execution.SuggestedCall)
		resp.Sources = append(resp.Sources, execution.Source)
		if execution.Success {
			resp.Executed = true
		} else {
			resp.Guidance = append(resp.Guidance, "Tool "+execution.Tool.Name+" failed: "+execution.Error)
		}
	}
	resp.Insights = insights
	if len(resp.ExecutedCalls) > 0 {
		resp.ExecutedCall = &resp.ExecutedCalls[0]
	}

	resp.Message = buildChatbotMessage(plan, insights)
	resp.ResultCards = buildChatbotCards(plan, insights)
	return resp
}

func buildChatbotMessage(plan *ChatPlan, insights map[string]interface{}) string {
	if plan == nil {
		return "Read-only lookup complete."
	}
	if v, ok := insights["ai_scheduling.explanation"]; ok {
		if explanation, ok := v.(*SchedulingExplanation); ok && explanation != nil && strings.TrimSpace(explanation.Summary) != "" {
			return explanation.Summary
		}
	}
	if v, ok := insights["ai_scheduling.delay_risk"]; ok {
		if risk, ok := v.(*DelayRiskDetail); ok && risk != nil && strings.TrimSpace(risk.Issue) != "" {
			return risk.Issue
		}
	}
	if _, ok := insights["dashboard.kpis"]; ok {
		return "Loaded the current dashboard KPI snapshot."
	}
	if _, ok := insights["dashboard.alerts"]; ok {
		return "Loaded the current operational alerts."
	}
	if _, ok := insights["jobs.get"]; ok {
		return "Loaded the current job state."
	}
	if _, ok := insights["jobs.list"]; ok {
		return "Loaded the current job overview."
	}
	if _, ok := insights["machines.list"]; ok {
		return "Loaded the current machine overview."
	}
	if _, ok := insights["inventory.materials"]; ok {
		return "Loaded the current inventory visibility snapshot."
	}
	return plan.PlanExplanation
}

func buildChatbotCards(plan *ChatPlan, insights map[string]interface{}) []dto.AIResultCard {
	cards := make([]dto.AIResultCard, 0, 3)

	if v, ok := insights["jobs.get"]; ok {
		if job, ok := v.(*domain.Job); ok && job != nil {
			cards = append(cards, dto.AIResultCard{
				Kind:    "job_status",
				Title:   "Job Status",
				Tone:    statusTone(job.Status),
				Summary: fmt.Sprintf("Job %s is currently %s.", job.JobID, job.Status),
				Metrics: []dto.AIResultMetric{
					{Label: "Product", Value: job.ProductID},
					{Label: "Priority", Value: job.Priority},
					{Label: "Quantity", Value: fmt.Sprintf("%d", job.QuantityTotal)},
					{Label: "Deadline", Value: formatTime(job.Deadline)},
				},
			})
		}
	}

	if v, ok := insights["ai_scheduling.delay_risk"]; ok {
		if risk, ok := v.(*DelayRiskDetail); ok && risk != nil {
			cards = append(cards, dto.AIResultCard{
				Kind:    "delay_risk",
				Title:   "Delay Risk",
				Tone:    riskTone(risk.RiskLevel),
				Summary: risk.Issue,
				Metrics: []dto.AIResultMetric{
					{Label: "Risk Level", Value: risk.RiskLevel},
					{Label: "Risk Score", Value: fmt.Sprintf("%.1f", risk.RiskScore)},
					{Label: "Projected Delay", Value: fmt.Sprintf("%d min", risk.DelayMinutes)},
				},
				Bullets: limitStrings(risk.Reasons, 6),
			})
		}
	}

	if v, ok := insights["ai_scheduling.explanation"]; ok {
		if explanation, ok := v.(*SchedulingExplanation); ok && explanation != nil {
			bullets := append([]string{}, explanation.KeyPoints...)
			bullets = append(bullets, explanation.RecommendedActions...)
			cards = append(cards, dto.AIResultCard{
				Kind:    "job_explanation",
				Title:   "Job Explanation",
				Tone:    "info",
				Summary: explanation.Summary,
				Bullets: limitStrings(bullets, 6),
			})
		}
	}

	if len(cards) == 0 {
		cards = append(cards, dto.AIResultCard{
			Kind:    "read_only_lookup",
			Title:   "Read-Only Lookup",
			Tone:    "info",
			Summary: plan.PlanExplanation,
		})
	}
	return cards
}
