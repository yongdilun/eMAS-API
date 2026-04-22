package service

import (
	"testing"
)

type stubToolRegistry struct {
	tools map[string]ChatToolDefinition
}

func (r stubToolRegistry) List() []ChatToolDefinition {
	out := make([]ChatToolDefinition, 0, len(r.tools))
	for _, t := range r.tools {
		out = append(out, t)
	}
	return out
}

func (r stubToolRegistry) Get(name string) (ChatToolDefinition, bool) {
	t, ok := r.tools[name]
	return t, ok
}

func TestKeywordChatPlanner_AmbiguousWhenNoMatch(t *testing.T) {
	planner := NewKeywordChatPlanner()
	reg := stubToolRegistry{tools: map[string]ChatToolDefinition{}}

	plan, err := planner.Plan("hello there", nil, reg)
	if err != nil {
		t.Fatalf("Plan() err: %v", err)
	}
	if plan == nil {
		t.Fatalf("expected plan, got nil")
	}
	if !plan.Ambiguous {
		t.Fatalf("expected ambiguous plan")
	}
	if len(plan.ClarificationPrompt) == 0 {
		t.Fatalf("expected clarification prompts")
	}
}

func TestKeywordChatPlanner_RejectsUnknownToolsInRegistry(t *testing.T) {
	planner := NewKeywordChatPlanner()
	// Registry is intentionally missing the dashboard tools so validation fails.
	reg := stubToolRegistry{
		tools: map[string]ChatToolDefinition{
			"jobs.list": {Name: "jobs.list", ReadOnly: true},
		},
	}

	_, err := planner.Plan("show dashboard kpis", nil, reg)
	if err == nil {
		t.Fatalf("expected error")
	}
}
