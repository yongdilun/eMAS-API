package handler

import (
	"errors"
	"net/http"
	"testing"

	"emas/internal/apperror"

	"gorm.io/gorm"
)

func TestStatusForErrorMapsBackendTaxonomy(t *testing.T) {
	tests := []struct {
		name string
		err  error
		want int
	}{
		{name: "validation", err: apperror.Validation("bad request"), want: http.StatusUnprocessableEntity},
		{name: "not found", err: apperror.NotFound("missing"), want: http.StatusNotFound},
		{name: "gorm not found", err: gorm.ErrRecordNotFound, want: http.StatusNotFound},
		{name: "conflict", err: apperror.Conflict("conflict"), want: http.StatusConflict},
		{name: "forbidden", err: apperror.Forbidden("forbidden"), want: http.StatusForbidden},
		{name: "internal", err: apperror.Internal("internal"), want: http.StatusInternalServerError},
		{name: "unknown", err: errors.New("boom"), want: http.StatusInternalServerError},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := statusForError(tt.err); got != tt.want {
				t.Fatalf("statusForError(%v) = %d, want %d", tt.err, got, tt.want)
			}
		})
	}
}
