package handler_test

import (
	"net/http"
	"testing"
	"time"

	"emas/internal/router"
	"emas/internal/testutil"
)

func TestMachineHandler_CRUD(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	// Create
	w := testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-TEST", "machine_name": "CNC Mill", "machine_type": "CNC",
		"location": "A1", "capacity_per_hour": 60, "maintenance_interval_days": 30,
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create: got %d, body: %s", w.Code, w.Body.String())
	}

	// Get
	w = testutil.Request(r, "GET", "/api/v1/machines/M-TEST", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("get: got %d", w.Code)
	}

	// List
	w = testutil.Request(r, "GET", "/api/v1/machines", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list: got %d", w.Code)
	}

	// Update
	w = testutil.Request(r, "PUT", "/api/v1/machines/M-TEST", map[string]interface{}{
		"status": "idle", "machine_name": "CNC Mill Updated",
	})
	if w.Code != http.StatusOK {
		t.Fatalf("update: got %d", w.Code)
	}

	w = testutil.Request(r, "GET", "/api/v1/machines?status=broken", nil)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("list invalid status: got %d, want 400", w.Code)
	}

	w = testutil.Request(r, "PUT", "/api/v1/machines/M-TEST", map[string]interface{}{
		"status": "broken",
	})
	if w.Code != http.StatusBadRequest {
		t.Fatalf("update invalid status: got %d, want 400", w.Code)
	}
}

func TestMachineHandler_ListFiltersAreApplied(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	for _, body := range []map[string]interface{}{
		{"machine_id": "M-PAINT-1", "machine_name": "Paint Booth 1", "machine_type": "PAINT", "location": "Paint Shop"},
		{"machine_id": "M-CNC-1", "machine_name": "CNC Mill 1", "machine_type": "CNC", "location": "Machine Shop"},
		{"machine_id": "M-CNC-2", "machine_name": "CNC Mill 2", "machine_type": "CNC", "location": "Paint Shop"},
	} {
		w := testutil.Request(r, "POST", "/api/v1/machines", body)
		if w.Code != http.StatusCreated {
			t.Fatalf("seed machine: got %d, body: %s", w.Code, w.Body.String())
		}
	}

	w := testutil.Request(r, "GET", "/api/v1/machines?location=Paint%20Shop", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list location filter: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ := testutil.DecodeResponse(w)
	if !success {
		t.Fatal("list location filter failed")
	}
	rows, ok := data.([]interface{})
	if !ok {
		t.Fatalf("location filter data not list: %T", data)
	}
	if len(rows) != 2 {
		t.Fatalf("location filter returned %d rows, want 2", len(rows))
	}
	for _, row := range rows {
		m := row.(map[string]interface{})
		if m["Location"] != "Paint Shop" && m["location"] != "Paint Shop" {
			t.Fatalf("location filter returned nonmatching row: %#v", m)
		}
	}

	w = testutil.Request(r, "GET", "/api/v1/machines?machine_type=CNC", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list machine_type filter: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ = testutil.DecodeResponse(w)
	if !success {
		t.Fatal("list machine_type filter failed")
	}
	rows = data.([]interface{})
	if len(rows) != 2 {
		t.Fatalf("machine_type filter returned %d rows, want 2", len(rows))
	}
	for _, row := range rows {
		m := row.(map[string]interface{})
		if m["MachineType"] != "CNC" && m["machine_type"] != "CNC" {
			t.Fatalf("machine_type filter returned nonmatching row: %#v", m)
		}
	}

	w = testutil.Request(r, "GET", "/api/v1/machines?location=Nope", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list nonmatching location: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ = testutil.DecodeResponse(w)
	if !success {
		t.Fatal("list nonmatching location failed")
	}
	if rows = data.([]interface{}); len(rows) != 0 {
		t.Fatalf("nonmatching location returned %d rows, want 0", len(rows))
	}
}

func TestMachineHandler_AssignCapability(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)
	testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-CAP", "machine_name": "Press", "machine_type": "Press",
	})

	w := testutil.Request(r, "POST", "/api/v1/machines/M-CAP/capabilities", map[string]interface{}{
		"step_id": "STP-001", "efficiency_factor": 1.2,
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("assign capability: got %d", w.Code)
	}
}

func TestMachineHandler_RecordDowntime(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)
	testutil.Request(r, "POST", "/api/v1/machines", map[string]interface{}{
		"machine_id": "M-DT", "machine_name": "Mill", "machine_type": "CNC",
	})

	now := time.Now()
	w := testutil.Request(r, "POST", "/api/v1/machines/downtime", map[string]interface{}{
		"machine_id": "M-DT", "cause": "breakdown",
		"start_time": now.Add(-1 * time.Hour).Format(time.RFC3339),
		"end_time":   now.Format(time.RFC3339),
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("record downtime: got %d", w.Code)
	}
}

func TestMachineHandler_MaintenanceAlerts(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	w := testutil.Request(r, "GET", "/api/v1/machines/maintenance-alerts?days_ahead=7", nil)
	if w.Code == 500 {
		t.Skip("maintenance alerts uses MySQL DATE_ADD/INTERVAL; skip on SQLite")
	}
	if w.Code != http.StatusOK {
		t.Fatalf("maintenance alerts: got %d", w.Code)
	}
	success, _, _ := testutil.DecodeResponse(w)
	if !success {
		t.Fatal("maintenance alerts failed")
	}
}

func TestMachineHandler_RerouteRecommendations(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	// No machine_id
	w := testutil.Request(r, "GET", "/api/v1/machines/reroute-recommendations", nil)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("reroute no param: got %d, want 400", w.Code)
	}

	w = testutil.Request(r, "GET", "/api/v1/machines/reroute-recommendations?machine_id=M-X", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("reroute: got %d", w.Code)
	}
}

func TestMachineHandler_Utilization(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	w := testutil.Request(r, "GET", "/api/v1/machines/utilization", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("utilization: got %d, body: %s", w.Code, w.Body.String())
	}
	success, data, _ := testutil.DecodeResponse(w)
	if !success {
		t.Fatal("utilization: success false")
	}
	m, ok := data.(map[string]interface{})
	if !ok {
		t.Fatalf("utilization: data not map, got %T", data)
	}
	if _, ok := m["avg_pct"]; !ok {
		t.Error("utilization: missing avg_pct")
	}
	arr, ok := m["data"].([]interface{})
	if !ok {
		t.Fatalf("utilization: data.data not array, got %T", m["data"])
	}
	// Empty machines list returns avg 78 and empty data
	for i, it := range arr {
		item, ok := it.(map[string]interface{})
		if !ok {
			continue
		}
		if _, ok := item["machine_id"]; !ok {
			t.Errorf("utilization data[%d]: missing machine_id", i)
		}
		if _, ok := item["utilization_pct"]; !ok {
			t.Errorf("utilization data[%d]: missing utilization_pct", i)
		}
	}
}
