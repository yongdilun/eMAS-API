package service

import (
	"reflect"
	"testing"
)

type TestQueryDTO struct {
	Status      string `form:"status,omitempty" binding:"omitempty,oneof=idle running"`
	Ignored     string `form:"-"`
	MachineType string `form:"machine_type"`
	NoFormTag   string
}

func TestExtractQueryParamMeta(t *testing.T) {
	meta := extractQueryParamMeta(TestQueryDTO{})

	if len(meta) != 2 {
		t.Errorf("Expected 2 params, got %d", len(meta))
	}

	if statusMeta, ok := meta["status"]; !ok {
		t.Error("Expected 'status' param to be extracted (ignoring omitempty)")
	} else if len(statusMeta.AllowedValues) != 2 || statusMeta.AllowedValues[0] != "idle" || statusMeta.AllowedValues[1] != "running" {
		t.Errorf("Expected allowed values [idle running], got %v", statusMeta.AllowedValues)
	}

	if _, ok := meta["Ignored"]; ok {
		t.Error("Expected 'Ignored' param to be skipped due to form:\"-\"")
	}

	if _, ok := meta["NoFormTag"]; ok {
		t.Error("Expected 'NoFormTag' param to be skipped due to missing form tag")
	}
}

func TestValidateQueryEntities(t *testing.T) {
	routeParams := extractQueryParamMeta(TestQueryDTO{})

	tests := []struct {
		name          string
		entities      map[string]interface{}
		wantAccepted  int
		wantRejected  int
		checkRejected func(*testing.T, []RejectedParam)
	}{
		{
			name: "valid params accepted",
			entities: map[string]interface{}{
				"status":       "idle",
				"machine_type": "CNC",
			},
			wantAccepted: 2,
			wantRejected: 0,
		},
		{
			name: "unknown params rejected",
			entities: map[string]interface{}{
				"status":  "running",
				"unknown": "value",
				"action":  "ignore_this", // should be ignored implicitly
			},
			wantAccepted: 1,
			wantRejected: 1,
			checkRejected: func(t *testing.T, rejected []RejectedParam) {
				if rejected[0].Field != "unknown" || rejected[0].Reason != "Unsupported filter" {
					t.Errorf("Unexpected rejected param: %+v", rejected[0])
				}
			},
		},
		{
			name: "invalid enum rejected with allowed values",
			entities: map[string]interface{}{
				"status": "broken",
			},
			wantAccepted: 0,
			wantRejected: 1,
			checkRejected: func(t *testing.T, rejected []RejectedParam) {
				if rejected[0].Field != "status" || rejected[0].Reason != "Invalid value" {
					t.Errorf("Unexpected rejected param: %+v", rejected[0])
				}
				if !reflect.DeepEqual(rejected[0].AllowedValues, []string{"idle", "running"}) {
					t.Errorf("Expected allowed values [idle running], got %v", rejected[0].AllowedValues)
				}
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			res := ValidateQueryEntities(tt.entities, routeParams)
			if len(res.AcceptedParams) != tt.wantAccepted {
				t.Errorf("Expected %d accepted params, got %d", tt.wantAccepted, len(res.AcceptedParams))
			}
			if len(res.RejectedParams) != tt.wantRejected {
				t.Errorf("Expected %d rejected params, got %d", tt.wantRejected, len(res.RejectedParams))
			}
			if tt.checkRejected != nil && len(res.RejectedParams) > 0 {
				tt.checkRejected(t, res.RejectedParams)
			}
		})
	}
}

func TestBuildQueryParamsAndRejectionMessage(t *testing.T) {
	accepted := map[string]string{
		"status": "running",
	}
	url := buildQueryParams("/api/v1/test", accepted)
	if url != "/api/v1/test?status=running" {
		t.Errorf("Unexpected URL: %s", url)
	}

	rejected := []RejectedParam{
		{Field: "unknown", Reason: "Unsupported filter"},
		{Field: "status", Reason: "Invalid value", AllowedValues: []string{"idle", "running"}},
	}
	msg := generateRejectionMessage(rejected)
	if msg == "" {
		t.Error("Expected rejection message")
	}
}
