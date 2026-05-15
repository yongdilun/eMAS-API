package handler_test

import (
	"net/http"
	"strings"
	"testing"
	"time"

	"emas/internal/domain"
	"emas/internal/router"
	"emas/internal/testutil"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func TestSchedulingHandler_Features(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)
	testSchedulingHandlerReadiness(t, r)
	testSchedulingHandlerCandidateMachines(t, r)
	testSchedulingHandlerPrecedence(t, r)
	testSchedulingHandlerSolverPreview(t, r)
	testSchedulingTrainingDatasetMaintenanceFlow(t, db, r)
}

func testSchedulingHandlerReadiness(t *testing.T, r *gin.Engine) {
	testutil.Request(r, "POST", "/api/v1/formulas", map[string]interface{}{
		"formula_id": "F-READY", "formula_name": "Ready Formula",
	})
	testutil.Request(r, "POST", "/api/v1/products", map[string]interface{}{
		"product_id": "P-READY", "product_name": "Ready Product", "formula_id": "F-READY",
	})
	testutil.Request(r, "POST", "/api/v1/inventory/materials", map[string]interface{}{
		"material_id": "MAT-READY", "material_name": "Steel Coil", "current_stock": 100, "unit": "kg",
	})
	testutil.Request(r, "POST", "/api/v1/formulas/F-READY/ingredients", map[string]interface{}{
		"material_id": "MAT-READY", "quantity_per_unit": 1, "unit": "kg",
	})

	now := time.Now().UTC()
	testutil.Request(r, "POST", "/api/v1/inventory/reservations", map[string]interface{}{
		"material_id": "MAT-READY", "reserved_qty": 80, "needed_at": now.Add(-1 * time.Minute).Format(time.RFC3339),
	})
	testutil.Request(r, "POST", "/api/v1/inventory/expected-arrivals", map[string]interface{}{
		"material_id": "MAT-READY", "quantity": 40, "expected_arrive_at": now.Add(2 * time.Hour).Format(time.RFC3339),
	})

	w := testutil.Request(r, "GET", "/api/v1/scheduling/products/P-READY/readiness?quantity=50", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("readiness: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, errMsg := testutil.DecodeResponse(w)
	if !success {
		t.Fatalf("readiness: success false: %s", errMsg)
	}
	payload := data.(map[string]interface{})
	if payload["can_start_now"].(bool) {
		t.Fatal("expected can_start_now to be false")
	}
	if _, ok := payload["earliest_ready_at"]; !ok {
		t.Fatalf("expected earliest_ready_at to be populated, payload=%#v", payload)
	}
}

func testSchedulingHandlerCandidateMachines(t *testing.T, r *gin.Engine) {
	testutil.Request(r, "POST", "/api/v1/products", map[string]interface{}{
		"product_id": "P-CAND", "product_name": "Candidate Product",
	})
	testutil.Request(r, "POST", "/api/v1/processes", map[string]interface{}{
		"process_id": "PRC-CAND", "product_id": "P-CAND", "process_name": "Candidate Process",
	})
	testutil.Request(r, "POST", "/api/v1/processes/PRC-CAND/steps", map[string]interface{}{
		"step_id": "STEP-CAND", "step_name": "Cut", "machine_type_required": "CNC",
	})
	testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-CAND", "machine_name": "Candidate CNC", "machine_type": "CNC",
	})

	w := testutil.Request(r, "GET", "/api/v1/scheduling/steps/STEP-CAND/candidate-machines", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("candidate machines: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ := testutil.DecodeResponse(w)
	if !success {
		t.Fatal("candidate machines: success false")
	}
	items := data.([]interface{})
	if len(items) == 0 {
		t.Fatal("expected candidate machines")
	}
}

func testSchedulingHandlerPrecedence(t *testing.T, r *gin.Engine) {
	testutil.Request(r, "POST", "/api/v1/products", map[string]interface{}{
		"product_id": "P-PREC", "product_name": "Precedence Product",
	})
	testutil.Request(r, "POST", "/api/v1/processes", map[string]interface{}{
		"process_id": "PRC-PREC", "product_id": "P-PREC", "process_name": "Precedence Process",
	})
	testutil.Request(r, "POST", "/api/v1/processes/PRC-PREC/steps", map[string]interface{}{
		"step_id": "STEP-PREC-1", "step_name": "Step 1", "machine_type_required": "CUT",
	})
	testutil.Request(r, "POST", "/api/v1/processes/PRC-PREC/steps", map[string]interface{}{
		"step_id": "STEP-PREC-2", "step_name": "Step 2", "machine_type_required": "WELD",
	})
	testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-WELD", "machine_name": "Welder", "machine_type": "WELD",
	})
	w := testutil.Request(r, "POST", "/api/v1/jobs", map[string]interface{}{
		"product_id": "P-PREC", "quantity_total": 10, "deadline": "2026-07-01T10:00:00Z",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create job: got %d, body: %s", w.Code, w.Body.String())
	}
	_, data, _ := testutil.DecodeResponse(w)
	jobID := data.(map[string]interface{})["job_id"].(string)
	w = testutil.Request(r, "GET", "/api/v1/jobs/"+jobID+"/steps", nil)
	_, data, _ = testutil.DecodeResponse(w)
	steps := data.([]interface{})
	if len(steps) < 2 {
		t.Fatalf("expected 2 steps, got %d", len(steps))
	}
	secondStepID := steps[1].(map[string]interface{})["job_step_id"].(string)

	start := time.Now().UTC().Add(1 * time.Hour)
	end := start.Add(1 * time.Hour)
	w = testutil.Request(r, "POST", "/api/v1/scheduling/slots/validate", map[string]interface{}{
		"job_step_id":     secondStepID,
		"machine_id":      "M-WELD",
		"scheduled_start": start.Format(time.RFC3339),
		"scheduled_end":   end.Format(time.RFC3339),
		"quantity":        10,
	})
	if w.Code != http.StatusOK {
		t.Fatalf("validate slot: got %d, body: %s", w.Code, w.Body.String())
	}
	_, data, _ = testutil.DecodeResponse(w)
	payload := data.(map[string]interface{})
	if payload["valid"].(bool) {
		t.Fatal("expected validation to fail for unscheduled predecessor")
	}
	reasons := payload["reasons"].([]interface{})
	foundPrecedence := false
	for _, reason := range reasons {
		if strings.Contains(reason.(string), "previous process step") {
			foundPrecedence = true
			break
		}
	}
	if !foundPrecedence {
		t.Fatalf("expected precedence reason, got %#v", reasons)
	}
}

func testSchedulingHandlerSolverPreview(t *testing.T, r *gin.Engine) {
	testutil.Request(r, "POST", "/api/v1/products", map[string]interface{}{
		"product_id": "P-SOLVE", "product_name": "Solver Product",
	})
	testutil.Request(r, "POST", "/api/v1/processes", map[string]interface{}{
		"process_id": "PRC-SOLVE", "product_id": "P-SOLVE", "process_name": "Solver Process",
	})
	testutil.Request(r, "POST", "/api/v1/processes/PRC-SOLVE/steps", map[string]interface{}{
		"step_id": "STEP-SOLVE", "step_name": "Mill", "machine_type_required": "CNC",
	})
	testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-SOLVE", "machine_name": "Solver CNC", "machine_type": "CNC", "capacity_per_hour": 60,
	})
	w := testutil.Request(r, "POST", "/api/v1/jobs", map[string]interface{}{
		"product_id": "P-SOLVE", "quantity_total": 20, "deadline": "2026-08-01T10:00:00Z",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create job: got %d, body: %s", w.Code, w.Body.String())
	}
	_, data, _ := testutil.DecodeResponse(w)
	jobID := data.(map[string]interface{})["job_id"].(string)

	w = testutil.Request(r, "GET", "/api/v1/scheduling/jobs/"+jobID+"/solver-preview", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("solver preview: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ := testutil.DecodeResponse(w)
	if !success {
		t.Fatal("solver preview: success false")
	}
	payload := data.(map[string]interface{})
	steps := payload["steps"].([]interface{})
	if len(steps) == 0 {
		t.Fatal("expected solver preview steps")
	}
}

func testSchedulingTrainingDatasetMaintenanceFlow(t *testing.T, db *gorm.DB, r *gin.Engine) {
	testutil.Request(r, "POST", "/api/v1/products", map[string]interface{}{
		"product_id": "P-TRAIN", "product_name": "Training Product",
	})
	testutil.Request(r, "POST", "/api/v1/processes", map[string]interface{}{
		"process_id": "PRC-TRAIN", "product_id": "P-TRAIN", "process_name": "Training Process",
	})
	testutil.Request(r, "POST", "/api/v1/processes/PRC-TRAIN/steps", map[string]interface{}{
		"step_id": "STEP-TRAIN", "step_name": "Training Step", "machine_type_required": "TRN",
	})
	testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-TRAIN", "machine_name": "Training Machine", "machine_type": "TRN",
	})
	w := testutil.Request(r, "POST", "/api/v1/jobs", map[string]interface{}{
		"product_id": "P-TRAIN", "quantity_total": 12, "deadline": "2026-08-05T10:00:00Z",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create training job: got %d, body: %s", w.Code, w.Body.String())
	}
	_, data, _ := testutil.DecodeResponse(w)
	jobID := data.(map[string]interface{})["job_id"].(string)
	w = testutil.Request(r, "POST", "/api/v1/job-steps", map[string]interface{}{"job_id": jobID})
	if w.Code != http.StatusCreated {
		t.Fatalf("create training job steps: got %d, body: %s", w.Code, w.Body.String())
	}
	w = testutil.Request(r, "GET", "/api/v1/jobs/"+jobID+"/steps", nil)
	_, data, _ = testutil.DecodeResponse(w)
	jobStepID := data.([]interface{})[0].(map[string]interface{})["job_step_id"].(string)
	w = testutil.Request(r, "POST", "/api/v1/job-steps/split", map[string]interface{}{
		"job_step_id": jobStepID,
		"splits": []map[string]interface{}{
			{"machine_id": "M-TRAIN", "start_time": "2026-08-03T02:00:00Z", "duration_mins": 60, "quantity": 12},
		},
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create training slot: got %d, body: %s", w.Code, w.Body.String())
	}

	if err := db.Exec("DELETE FROM ml_training_events").Error; err != nil {
		t.Fatalf("clear ml_training_events: %v", err)
	}

	w = testutil.Request(r, "GET", "/api/v1/scheduling/training-dataset", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("training dataset export: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ := testutil.DecodeResponse(w)
	if !success {
		t.Fatal("training dataset export: success false")
	}
	if len(data.([]interface{})) != 0 {
		t.Fatal("expected read-only export to stay empty after explicit delete")
	}

	w = testutil.Request(r, "GET", "/api/v1/scheduling/training-dataset/stats", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("training dataset stats: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ = testutil.DecodeResponse(w)
	if !success {
		t.Fatal("training dataset stats: success false")
	}
	if int(data.(map[string]interface{})["total_rows"].(float64)) != 0 {
		t.Fatal("expected zero rows before explicit backfill")
	}

	w = testutil.RequestWithHeaders(r, "POST", "/api/v1/scheduling/training-dataset/backfill", nil, map[string]string{
		"X-User-Id":   "test-planner",
		"X-User-Role": "planner",
	})
	if w.Code != http.StatusOK {
		t.Fatalf("training dataset backfill: got %d, body: %s", w.Code, w.Body.String())
	}

	var count int64
	if err := db.Model(&domain.MLTrainingEvent{}).Count(&count).Error; err != nil {
		t.Fatalf("count training rows after backfill: %v", err)
	}
	if count == 0 {
		t.Fatal("expected explicit backfill to repopulate training rows")
	}
}
