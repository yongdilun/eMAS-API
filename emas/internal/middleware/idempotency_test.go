package middleware_test

import (
	"net/http"
	"sync"
	"sync/atomic"
	"testing"
	"time"

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

func TestIdempotencyMiddlewareConcurrentSameKeyExecutesHandlerOnce(t *testing.T) {
	db := testutil.NewTestDB(t)
	if sqlDB, err := db.DB(); err == nil {
		sqlDB.SetMaxOpenConns(4)
		sqlDB.SetMaxIdleConns(4)
		defer sqlDB.SetMaxOpenConns(1)
		defer sqlDB.SetMaxIdleConns(1)
	}
	r := gin.New()
	r.Use(middleware.IdempotencyMiddleware(db))
	var handlerCalls int32
	r.POST("/concurrent", func(c *gin.Context) {
		atomic.AddInt32(&handlerCalls, 1)
		time.Sleep(25 * time.Millisecond)
		c.JSON(http.StatusCreated, dto.Response{Success: true, Data: map[string]string{"created": "true"}})
	})

	const requests = 8
	statuses := make(chan int, requests)
	replayed := make(chan bool, requests)
	var wg sync.WaitGroup
	wg.Add(requests)
	for i := 0; i < requests; i++ {
		go func() {
			defer wg.Done()
			w := testutil.RequestWithHeaders(r, http.MethodPost, "/concurrent", map[string]interface{}{"payload": "same"}, map[string]string{
				"Idempotency-Key": "idem-concurrent-key",
			})
			statuses <- w.Code
			replayed <- w.Header().Get("X-Idempotent-Replayed") == "true"
		}()
	}
	wg.Wait()
	close(statuses)
	close(replayed)

	for code := range statuses {
		if code != http.StatusCreated {
			t.Fatalf("status = %d, want 201", code)
		}
	}
	replayCount := 0
	for wasReplayed := range replayed {
		if wasReplayed {
			replayCount++
		}
	}
	if got := atomic.LoadInt32(&handlerCalls); got != 1 {
		t.Fatalf("handler calls = %d, want 1", got)
	}
	if replayCount != requests-1 {
		t.Fatalf("replayed responses = %d, want %d", replayCount, requests-1)
	}
}
