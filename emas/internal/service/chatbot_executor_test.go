package service

import (
	"context"
	"os"
	"testing"
)

func TestRegistryBackedReadOnlyExecutor_EnforcesRequiredArgs(t *testing.T) {
	reg := stubToolRegistry{
		tools: map[string]ChatToolDefinition{
			"jobs.get": {
				Name:         "jobs.get",
				Path:         "/api/v1/jobs/:job_id",
				ReadOnly:     true,
				RequiredArgs: []string{"job_id"},
				Execute: func(context.Context, map[string]interface{}) (interface{}, error) {
					return map[string]interface{}{"ok": true}, nil
				},
			},
		},
	}

	exec := NewRegistryBackedReadOnlyExecutor(reg, nil)
	_, err := exec.Execute(context.Background(), "C-1", "T-1", []ChatToolCall{
		{Name: "jobs.get", Args: map[string]interface{}{}},
	})
	if err == nil {
		t.Fatalf("expected error")
	}
}

func TestRegistryBackedReadOnlyExecutor_EnforcesReadOnly(t *testing.T) {
	reg := stubToolRegistry{
		tools: map[string]ChatToolDefinition{
			"unsafe.write": {
				Name:     "unsafe.write",
				ReadOnly: false,
				Execute: func(context.Context, map[string]interface{}) (interface{}, error) {
					return map[string]interface{}{"ok": true}, nil
				},
			},
		},
	}

	exec := NewRegistryBackedReadOnlyExecutor(reg, nil)
	_, err := exec.Execute(context.Background(), "C-1", "T-1", []ChatToolCall{
		{Name: "unsafe.write", Args: map[string]interface{}{}},
	})
	if err == nil {
		t.Fatalf("expected error")
	}
}

func TestRegistryBackedReadOnlyExecutor_RespectsMaxToolCalls(t *testing.T) {
	prev := os.Getenv("CHATBOT_MAX_TOOL_CALLS")
	t.Cleanup(func() { _ = os.Setenv("CHATBOT_MAX_TOOL_CALLS", prev) })
	_ = os.Setenv("CHATBOT_MAX_TOOL_CALLS", "1")

	reg := stubToolRegistry{
		tools: map[string]ChatToolDefinition{
			"a": {
				Name:     "a",
				Path:     "/a",
				ReadOnly: true,
				Execute: func(context.Context, map[string]interface{}) (interface{}, error) {
					return map[string]interface{}{"a": true}, nil
				},
			},
			"b": {
				Name:     "b",
				Path:     "/b",
				ReadOnly: true,
				Execute: func(context.Context, map[string]interface{}) (interface{}, error) {
					return map[string]interface{}{"b": true}, nil
				},
			},
		},
	}

	exec := NewRegistryBackedReadOnlyExecutor(reg, nil)
	results, err := exec.Execute(context.Background(), "C-1", "T-1", []ChatToolCall{
		{Name: "a", Args: map[string]interface{}{}},
		{Name: "b", Args: map[string]interface{}{}},
	})
	if err != nil {
		t.Fatalf("Execute() err: %v", err)
	}
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].Tool.Name != "a" {
		t.Fatalf("expected tool a, got %s", results[0].Tool.Name)
	}
}
