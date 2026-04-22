package handler_test

import (
	"emas/internal/domain"
	"emas/internal/router"
	"emas/internal/testutil"
	"encoding/json"
	"os"
	"testing"
)

type apiResp struct {
	Success bool            `json:"success"`
	Data    json.RawMessage `json:"data"`
	Error   string          `json:"error"`
}

func TestAIChats_Phase0ChatbotPipeline_PersistsAuditAndSources(t *testing.T) {
	prevV2 := os.Getenv("CHATBOT_V2_ENABLED")
	prevLegacy := os.Getenv("AI_CHAT_LEGACY_ENABLED")
	t.Cleanup(func() {
		_ = os.Setenv("CHATBOT_V2_ENABLED", prevV2)
		_ = os.Setenv("AI_CHAT_LEGACY_ENABLED", prevLegacy)
	})
	_ = os.Setenv("CHATBOT_V2_ENABLED", "true")
	_ = os.Setenv("AI_CHAT_LEGACY_ENABLED", "true")

	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	// 1) Create conversation
	w := testutil.Request(r, "POST", "/api/v1/ai/chats", map[string]interface{}{"title": "phase0"})
	if w.Code != 201 {
		t.Fatalf("expected 201, got %d: %s", w.Code, w.Body.String())
	}
	var createResp apiResp
	if err := json.Unmarshal(w.Body.Bytes(), &createResp); err != nil {
		t.Fatalf("unmarshal create resp: %v", err)
	}
	if !createResp.Success {
		t.Fatalf("create failed: %s", createResp.Error)
	}
	var conv struct {
		ID string `json:"id"`
	}
	if err := json.Unmarshal(createResp.Data, &conv); err != nil {
		t.Fatalf("unmarshal conv data: %v", err)
	}
	if conv.ID == "" {
		t.Fatalf("expected conversation id")
	}

	// 2) Send message that maps to read-only tools and succeeds without fixtures.
	w = testutil.Request(r, "POST", "/api/v1/ai/chats/"+conv.ID+"/messages", map[string]interface{}{"query": "show dashboard kpis"})
	if w.Code != 200 {
		t.Fatalf("expected 200, got %d: %s", w.Code, w.Body.String())
	}
	var msgResp apiResp
	if err := json.Unmarshal(w.Body.Bytes(), &msgResp); err != nil {
		t.Fatalf("unmarshal msg resp: %v", err)
	}
	if !msgResp.Success {
		t.Fatalf("send message failed: %s", msgResp.Error)
	}

	var cmd struct {
		ExecutionMode string          `json:"execution_mode"`
		Sources       json.RawMessage `json:"sources"`
		ExecutedCalls json.RawMessage `json:"executed_calls"`
	}
	if err := json.Unmarshal(msgResp.Data, &cmd); err != nil {
		t.Fatalf("unmarshal command resp: %v", err)
	}
	if cmd.ExecutionMode != "executed_readonly" {
		t.Fatalf("expected executed_readonly, got %q", cmd.ExecutionMode)
	}
	if len(cmd.Sources) == 0 || string(cmd.Sources) == "null" || string(cmd.Sources) == "[]" {
		t.Fatalf("expected non-empty sources; got %s", string(cmd.Sources))
	}
	if len(cmd.ExecutedCalls) == 0 || string(cmd.ExecutedCalls) == "null" || string(cmd.ExecutedCalls) == "[]" {
		t.Fatalf("expected non-empty executed_calls; got %s", string(cmd.ExecutedCalls))
	}

	// 3) Verify turn audit row exists (proves new stack ran).
	var audits []domain.ChatbotTurnAudit
	if err := db.Find(&audits).Error; err != nil {
		t.Fatalf("list audits: %v", err)
	}
	if len(audits) == 0 {
		t.Fatalf("expected audits to be created")
	}
}
