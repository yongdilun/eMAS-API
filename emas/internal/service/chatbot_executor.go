package service

import (
	"context"
	"emas/internal/domain"
	"emas/internal/handler/dto"
	"emas/pkg/featureflags"
	"emas/pkg/id"
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

type RegistryBackedReadOnlyExecutor struct {
	registry     ToolRegistry
	snapshotRepo ChatToolSnapshotRepository
}

func NewRegistryBackedReadOnlyExecutor(registry ToolRegistry, snapshotRepo ChatToolSnapshotRepository) *RegistryBackedReadOnlyExecutor {
	return &RegistryBackedReadOnlyExecutor{registry: registry, snapshotRepo: snapshotRepo}
}

func (e *RegistryBackedReadOnlyExecutor) Execute(ctx context.Context, conversationID string, turnAuditID string, calls []ChatToolCall) ([]ChatToolExecutionResult, error) {
	if e == nil || e.registry == nil {
		return nil, fmt.Errorf("executor not configured")
	}

	maxCalls := featureflags.ChatbotMaxToolCalls()
	if maxCalls > 0 && len(calls) > maxCalls {
		calls = calls[:maxCalls]
	}

	results := make([]ChatToolExecutionResult, 0, len(calls))
	for _, call := range calls {
		tool, ok := e.registry.Get(call.Name)
		if !ok {
			return nil, fmt.Errorf("unknown tool: %s", call.Name)
		}
		if !tool.ReadOnly {
			return nil, fmt.Errorf("tool %s is not read-only", call.Name)
		}
		for _, key := range tool.RequiredArgs {
			if strings.TrimSpace(chatArgString(call.Args, key)) == "" {
				return nil, fmt.Errorf("missing required arg %s for tool %s", key, call.Name)
			}
		}

		start := time.Now()
		output, err := tool.Execute(ctx, call.Args)
		latency := int(time.Since(start).Milliseconds())

		inputJSON, _ := json.Marshal(call.Args)
		outputJSON, _ := json.Marshal(output)

		res := ChatToolExecutionResult{
			Tool:      tool,
			Call:      call,
			Output:    output,
			LatencyMs: latency,
			Success:   err == nil,
			Source: dto.AISourceRef{
				Kind:        "internal_tool",
				Name:        tool.Name,
				Path:        tool.Path,
				ReadOnly:    true,
				Description: tool.Description,
			},
			SuggestedCall: dto.AISuggestedCall{
				Method:           "GET",
				Path:             interpolateToolPath(tool.Path, call.Args),
				Purpose:          tool.Description,
				RequiresApproval: false,
			},
		}
		if err != nil {
			res.Error = err.Error()
		}

		if e.snapshotRepo != nil {
			_ = e.snapshotRepo.Create(&domain.ChatbotToolExecutionSnapshot{
				ID:             id.NewPrefixed("CHATSNAP-"),
				TurnAuditID:    turnAuditID,
				ConversationID: conversationID,
				ToolName:       tool.Name,
				ToolVersion:    tool.Version,
				SchemaVersion:  tool.SchemaVersion,
				InputJSON:      string(inputJSON),
				OutputJSON:     string(outputJSON),
				LatencyMs:      latency,
				Success:        err == nil,
				Error:          res.Error,
				CreatedAt:      time.Now().UTC(),
			})
		}

		results = append(results, res)
	}
	return results, nil
}

func interpolateToolPath(path string, args map[string]interface{}) string {
	out := path
	for key, value := range args {
		if s, ok := value.(string); ok && s != "" {
			out = strings.ReplaceAll(out, ":"+key, s)
		}
	}
	return out
}
