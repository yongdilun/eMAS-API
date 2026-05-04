package e2e_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http/httptest"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"emas/internal/router"
	"emas/internal/testutil"

	"github.com/gin-gonic/gin"
)

type scenario struct {
	ID                       string            `json:"id"`
	Category                 string            `json:"category"`
	Input                    string            `json:"input"`
	Entrypoint               string            `json:"entrypoint"`
	SeedProfile              string            `json:"seed_profile"`
	ExpectedIntent           string            `json:"expected_intent"`
	ExpectedTools            []string          `json:"expected_tools"`
	ApprovalPolicy           string            `json:"approval_policy"`
	ExpectedStatus           int               `json:"expected_status"`
	Headers                  map[string]string `json:"headers"`
	Request                  *scenarioRequest  `json:"request"`
	RawRequest               *rawRequest       `json:"raw_request"`
	SetupRequest             *scenarioRequest  `json:"setup_request"`
	ExpectedResponseContains []string          `json:"expected_response_contains"`
}

type scenarioRequest struct {
	Method string      `json:"method"`
	Path   string      `json:"path"`
	Body   interface{} `json:"body"`
}

type rawRequest struct {
	Method string `json:"method"`
	Path   string `json:"path"`
	Body   string `json:"body"`
}

func TestSeedPipelineManifestHasRequiredCoverage(t *testing.T) {
	scenarios := loadSeedPipelineScenarios(t)
	if len(scenarios) < 60 {
		t.Fatalf("expected at least 60 scenarios, got %d", len(scenarios))
	}

	required := map[string]int{
		"intent":        10,
		"backend_read":  10,
		"crud":          10,
		"scheduling":    10,
		"approval":      10,
		"factory_agent": 10,
	}
	counts := map[string]int{}
	ids := map[string]bool{}
	for _, sc := range scenarios {
		if sc.ID == "" || sc.Input == "" || sc.Entrypoint == "" || sc.SeedProfile == "" {
			t.Fatalf("scenario has required blank field: %+v", sc)
		}
		if ids[sc.ID] {
			t.Fatalf("duplicate scenario id %q", sc.ID)
		}
		ids[sc.ID] = true
		counts[sc.Category]++
		if sc.ApprovalPolicy == "" {
			t.Fatalf("scenario %s missing approval_policy", sc.ID)
		}
	}
	for category, want := range required {
		if counts[category] < want {
			t.Fatalf("category %s expected >= %d scenarios, got %d", category, want, counts[category])
		}
	}
	if counts["negative"] < 10 {
		t.Fatalf("expected >= 10 negative scenarios, got %d", counts["negative"])
	}
}

func TestSeedPipelineCanonicalFingerprint(t *testing.T) {
	db := testutil.NewTestDB(t)
	testutil.SeedCanonical(t, db)
}

func TestSeedPipelineSeededScenariosOptIn(t *testing.T) {
	if os.Getenv("E2E_SEEDED") != "1" {
		t.Skip("set E2E_SEEDED=1 to run seeded input-to-output scenarios")
	}

	prevAuth := os.Getenv("AI_AUTH_REQUIRED")
	prevChatbot := os.Getenv("CHATBOT_V2_ENABLED")
	prevLegacyChat := os.Getenv("AI_CHAT_LEGACY_ENABLED")
	t.Cleanup(func() {
		_ = os.Setenv("AI_AUTH_REQUIRED", prevAuth)
		_ = os.Setenv("CHATBOT_V2_ENABLED", prevChatbot)
		_ = os.Setenv("AI_CHAT_LEGACY_ENABLED", prevLegacyChat)
	})
	_ = os.Setenv("AI_AUTH_REQUIRED", "true")
	_ = os.Setenv("CHATBOT_V2_ENABLED", "true")
	_ = os.Setenv("AI_CHAT_LEGACY_ENABLED", "true")

	runID := time.Now().UTC().Format("20060102T150405Z")
	artifactDir := filepath.Join(repoRoot(t), "test-artifacts", runID)
	if err := os.MkdirAll(artifactDir, 0o755); err != nil {
		t.Fatal(err)
	}

	for _, sc := range loadSeedPipelineScenarios(t) {
		if sc.Entrypoint == "factory_agent" || sc.Entrypoint == "go_ai_command_stub" || sc.Request == nil && sc.RawRequest == nil {
			writeScenarioArtifact(t, artifactDir, sc, map[string]interface{}{
				"status": "skipped",
				"reason": "handled by Python fast/live suites or stub-specific tests",
			})
			continue
		}
		t.Run(sc.ID, func(t *testing.T) {
			db := testutil.NewTestDB(t)
			testutil.SeedCanonical(t, db)
			r := testutil.NewTestRouter(db, router.Setup)

			resolvedPath := ""
			if sc.SetupRequest != nil {
				setup := performJSONRequest(t, r, *sc.SetupRequest, sc.Headers)
				if setup.Code < 200 || setup.Code >= 300 {
					t.Fatalf("setup request failed: status=%d body=%s", setup.Code, setup.Body.String())
				}
				resolvedPath = resolveSetupPath(t, sc.Request.Path, setup.Body.Bytes())
			}

			var w *httptest.ResponseRecorder
			if sc.RawRequest != nil {
				w = performRawRequest(t, r, *sc.RawRequest, sc.Headers)
			} else {
				req := *sc.Request
				if resolvedPath != "" {
					req.Path = resolvedPath
				}
				w = performJSONRequest(t, r, req, sc.Headers)
			}

			result := map[string]interface{}{
				"status":        "ran",
				"http_status":   w.Code,
				"response_body": w.Body.String(),
			}
			writeScenarioArtifact(t, artifactDir, sc, result)

			if w.Code != sc.ExpectedStatus {
				t.Fatalf("expected status %d, got %d body=%s", sc.ExpectedStatus, w.Code, w.Body.String())
			}
			body := strings.ToLower(w.Body.String())
			for _, want := range sc.ExpectedResponseContains {
				if !strings.Contains(body, strings.ToLower(want)) {
					t.Fatalf("response missing %q: %s", want, w.Body.String())
				}
			}
		})
	}
}

func loadSeedPipelineScenarios(t *testing.T) []scenario {
	t.Helper()
	path := filepath.Join(repoRoot(t), "tests", "e2e", "scenarios", "seed_pipeline.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var scenarios []scenario
	if err := json.Unmarshal(raw, &scenarios); err != nil {
		t.Fatalf("parse %s: %v", path, err)
	}
	return scenarios
}

func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("runtime caller unavailable")
	}
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", ".."))
}

func performJSONRequest(t *testing.T, r *gin.Engine, req scenarioRequest, headers map[string]string) *httptest.ResponseRecorder {
	t.Helper()
	var body *bytes.Reader
	if req.Body == nil {
		body = bytes.NewReader(nil)
	} else {
		raw, err := json.Marshal(req.Body)
		if err != nil {
			t.Fatalf("marshal request body: %v", err)
		}
		body = bytes.NewReader(raw)
	}
	httpReq := httptest.NewRequest(req.Method, req.Path, body)
	if req.Body != nil {
		httpReq.Header.Set("Content-Type", "application/json")
	}
	for key, value := range headers {
		httpReq.Header.Set(key, value)
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httpReq)
	return w
}

func performRawRequest(t *testing.T, r *gin.Engine, req rawRequest, headers map[string]string) *httptest.ResponseRecorder {
	t.Helper()
	httpReq := httptest.NewRequest(req.Method, req.Path, strings.NewReader(req.Body))
	httpReq.Header.Set("Content-Type", "application/json")
	for key, value := range headers {
		httpReq.Header.Set(key, value)
	}
	w := httptest.NewRecorder()
	r.ServeHTTP(w, httpReq)
	return w
}

func resolveSetupPath(t *testing.T, template string, setupBody []byte) string {
	t.Helper()
	if !strings.HasPrefix(template, "$setup.data.") {
		return template
	}
	field := strings.TrimPrefix(template, "$setup.data.")
	var wrapped struct {
		Data map[string]interface{} `json:"data"`
	}
	if err := json.Unmarshal(setupBody, &wrapped); err != nil {
		t.Fatalf("parse setup body: %v", err)
	}
	value := fmt.Sprint(wrapped.Data[field])
	if value == "" || value == "<nil>" {
		t.Fatalf("setup response missing data.%s: %s", field, string(setupBody))
	}
	return "/api/v1/jobs/" + value
}

func writeScenarioArtifact(t *testing.T, artifactDir string, sc scenario, result map[string]interface{}) {
	t.Helper()
	payload := map[string]interface{}{
		"scenario": sc,
		"result":   result,
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(artifactDir, sc.ID+".json")
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		t.Fatal(err)
	}
}
