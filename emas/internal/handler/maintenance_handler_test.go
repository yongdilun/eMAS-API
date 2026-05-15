package handler_test

import (
	"net/http"
	"testing"
	"time"

	"emas/internal/router"
	"emas/internal/testutil"
)

func TestMaintenanceHandler_RecordMaintenance(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)
	testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-MNT", "machine_name": "Mill", "machine_type": "CNC",
	})

	now := time.Now()
	w := testutil.Request(r, "POST", "/api/v1/maintenance", map[string]interface{}{
		"machine_id": "M-MNT", "maintenance_type": "preventive",
		"technician": "Jane", "description": "Routine check",
		"start_time": now.Add(-2 * time.Hour), "end_time": now,
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("record maintenance: got %d", w.Code)
	}

	w = testutil.Request(r, "POST", "/api/v1/maintenance", map[string]interface{}{
		"machine_id": "M-MNT", "maintenance_type": "preventive",
		"start_time": now, "end_time": now.Add(-1 * time.Hour),
	})
	if w.Code != http.StatusUnprocessableEntity {
		t.Fatalf("record maintenance invalid time window: got %d, want 422, body: %s", w.Code, w.Body.String())
	}
	success, _, errMsg := testutil.DecodeResponse(w)
	if success || errMsg == "" {
		t.Fatalf("record maintenance invalid time window envelope: success=%v error=%q", success, errMsg)
	}
}
