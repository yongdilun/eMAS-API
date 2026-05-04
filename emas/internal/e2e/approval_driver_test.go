package e2e_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"

	"emas/internal/domain"
	"emas/internal/router"
	"emas/internal/testutil"
)

func TestSeedPipelineChatbotApprovalDriver(t *testing.T) {
	prevV2 := os.Getenv("CHATBOT_V2_ENABLED")
	prevLegacy := os.Getenv("AI_CHAT_LEGACY_ENABLED")
	t.Cleanup(func() {
		_ = os.Setenv("CHATBOT_V2_ENABLED", prevV2)
		_ = os.Setenv("AI_CHAT_LEGACY_ENABLED", prevLegacy)
	})
	_ = os.Setenv("CHATBOT_V2_ENABLED", "true")
	_ = os.Setenv("AI_CHAT_LEGACY_ENABLED", "true")

	runID := time.Now().UTC().Format("20060102T150405Z")
	artifactDir := filepath.Join(repoRoot(t), "test-artifacts", runID)
	if err := os.MkdirAll(artifactDir, 0o755); err != nil {
		t.Fatal(err)
	}

	for _, policy := range []string{"approve", "reject"} {
		t.Run(policy, func(t *testing.T) {
			db := testutil.NewTestDB(t)
			testutil.SeedCanonical(t, db)
			r := testutil.NewTestRouter(db, router.Setup)

			create := testutil.Request(r, "POST", "/api/v1/ai/chats", map[string]interface{}{"title": "approval " + policy})
			if create.Code != 201 {
				t.Fatalf("create chat: status=%d body=%s", create.Code, create.Body.String())
			}
			var createResp struct {
				Success bool `json:"success"`
				Data    struct {
					ID string `json:"id"`
				} `json:"data"`
			}
			if err := json.Unmarshal(create.Body.Bytes(), &createResp); err != nil {
				t.Fatal(err)
			}

			msg := testutil.Request(r, "POST", "/api/v1/ai/chats/"+createResp.Data.ID+"/messages", map[string]interface{}{
				"query": "create job for PRD-A qty 2",
			})
			if msg.Code != 200 {
				t.Fatalf("message: status=%d body=%s", msg.Code, msg.Body.String())
			}

			pending := testutil.Request(r, "GET", "/api/v1/ai/chats/"+createResp.Data.ID+"/approvals", nil)
			if pending.Code != 200 {
				t.Fatalf("pending: status=%d body=%s", pending.Code, pending.Body.String())
			}
			var pendingResp struct {
				Success bool                     `json:"success"`
				Data    []domain.ChatbotApproval `json:"data"`
			}
			if err := json.Unmarshal(pending.Body.Bytes(), &pendingResp); err != nil {
				t.Fatal(err)
			}
			if len(pendingResp.Data) != 1 {
				t.Fatalf("expected exactly one pending approval, got %d body=%s", len(pendingResp.Data), pending.Body.String())
			}
			if pendingResp.Data[0].Status != "PENDING" {
				t.Fatalf("expected PENDING before decision, got %s", pendingResp.Data[0].Status)
			}

			path := "/api/v1/ai/chatbot/approvals/" + pendingResp.Data[0].ID + "/" + policy
			body := map[string]interface{}{}
			if policy == "reject" {
				body["reason"] = "seed pipeline rejection"
			}
			decision := testutil.Request(r, "POST", path, body)
			if decision.Code != 200 {
				t.Fatalf("decision: status=%d body=%s", decision.Code, decision.Body.String())
			}

			after := testutil.Request(r, "GET", "/api/v1/ai/chatbot/approvals/"+pendingResp.Data[0].ID, nil)
			if after.Code != 200 {
				t.Fatalf("after: status=%d body=%s", after.Code, after.Body.String())
			}
			var afterResp struct {
				Success bool                   `json:"success"`
				Data    domain.ChatbotApproval `json:"data"`
			}
			if err := json.Unmarshal(after.Body.Bytes(), &afterResp); err != nil {
				t.Fatal(err)
			}
			want := "EXECUTED"
			if policy == "reject" {
				want = "REJECTED"
			}
			if afterResp.Data.Status != want {
				t.Fatalf("expected %s after %s, got %s body=%s", want, policy, afterResp.Data.Status, after.Body.String())
			}
			artifactPath := filepath.Join(artifactDir, "approval-driver-"+policy+".json")
			artifact := map[string]interface{}{
				"scenario": map[string]interface{}{
					"id":              "approval-driver-" + policy,
					"input":           "create job for PRD-A qty 2",
					"approval_policy": policy,
				},
				"result": map[string]interface{}{
					"chat_id":               createResp.Data.ID,
					"message_status":        msg.Code,
					"pending_status":        pendingResp.Data[0].Status,
					"approval_id":           pendingResp.Data[0].ID,
					"decision_status":       decision.Code,
					"final_approval_status": afterResp.Data.Status,
					"passed":                true,
				},
			}
			b, err := json.MarshalIndent(artifact, "", "  ")
			if err != nil {
				t.Fatal(err)
			}
			if err := os.WriteFile(artifactPath, b, 0o644); err != nil {
				t.Fatal(err)
			}
			t.Logf("approval artifact: %s", artifactPath)
		})
	}
}
