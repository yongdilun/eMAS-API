package middleware_test

import (
	"net/http"
	"testing"

	"emas/internal/handler/dto"
	"emas/internal/middleware"
	"emas/internal/testutil"

	"github.com/gin-gonic/gin"
)

func TestIdempotencyMiddlewareConflictUsesStandardEnvelope(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := gin.New()
	r.Use(middleware.IdempotencyMiddleware(db))
	r.POST("/contract", func(c *gin.Context) {
		c.JSON(http.StatusCreated, dto.Response{Success: true, Data: map[string]string{"ok": "true"}})
	})

	req := func(body map[string]interface{}) (int, bool, string) {
		w := testutil.RequestWithHeaders(r, http.MethodPost, "/contract", body, map[string]string{
			"Idempotency-Key": "idem-contract-key",
		})
		success, _, errMsg := testutil.DecodeResponse(w)
		return w.Code, success, errMsg
	}

	code, success, errMsg := req(map[string]interface{}{
		"payload": "first",
	})
	if code != http.StatusCreated || !success || errMsg != "" {
		t.Fatalf("initial idempotent request: code=%d success=%v error=%q", code, success, errMsg)
	}

	code, success, errMsg = req(map[string]interface{}{
		"payload": "second",
	})
	if code != http.StatusConflict {
		t.Fatalf("conflicting idempotent request: got %d, want 409", code)
	}
	if success || errMsg == "" {
		t.Fatalf("conflicting idempotent request envelope: success=%v error=%q", success, errMsg)
	}
}
