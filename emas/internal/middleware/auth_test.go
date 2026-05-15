package middleware_test

import (
	"net/http"
	"testing"

	"emas/internal/handler/dto"
	"emas/internal/middleware"
	"emas/internal/testutil"

	"github.com/gin-gonic/gin"
)

func TestRequireRolesProtectedRouteRequiresIdentityAndRoleWhenAuthEnabled(t *testing.T) {
	t.Setenv("AI_AUTH_REQUIRED", "true")
	r := gin.New()
	r.POST("/protected", middleware.RequireRoles("planner", "manager", "admin"), func(c *gin.Context) {
		c.JSON(http.StatusOK, dto.Response{Success: true})
	})

	tests := []struct {
		name    string
		headers map[string]string
		want    int
	}{
		{name: "missing headers", headers: nil, want: http.StatusUnauthorized},
		{name: "missing role", headers: map[string]string{"X-User-Id": "user-1"}, want: http.StatusUnauthorized},
		{name: "invalid role", headers: map[string]string{"X-User-Id": "user-1", "X-User-Role": "viewer"}, want: http.StatusForbidden},
		{name: "allowed role", headers: map[string]string{"X-User-Id": "user-1", "X-User-Role": "planner"}, want: http.StatusOK},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := testutil.RequestWithHeaders(r, http.MethodPost, "/protected", nil, tt.headers)
			if w.Code != tt.want {
				t.Fatalf("status = %d, want %d, body=%s", w.Code, tt.want, w.Body.String())
			}
		})
	}
}

func TestRequireRolesKeepsLocalDefaultsWhenAuthDisabled(t *testing.T) {
	t.Setenv("AI_AUTH_REQUIRED", "false")
	r := gin.New()
	r.POST("/protected", middleware.RequireRoles("planner"), func(c *gin.Context) {
		userID, _ := c.Get(middleware.ContextUserIDKey)
		role, _ := c.Get(middleware.ContextUserRoleKey)
		c.JSON(http.StatusOK, dto.Response{Success: true, Data: map[string]interface{}{
			"user_id": userID,
			"role":    role,
		}})
	})

	w := testutil.RequestWithHeaders(r, http.MethodPost, "/protected", nil, nil)
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200, body=%s", w.Code, w.Body.String())
	}
}
