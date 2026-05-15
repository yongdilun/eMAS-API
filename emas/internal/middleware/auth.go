package middleware

import (
	"emas/internal/handler/dto"
	"emas/pkg/featureflags"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

const (
	ContextUserIDKey   = "user_id"
	ContextUserRoleKey = "user_role"
)

func RequireRoles(roles ...string) gin.HandlerFunc {
	allowed := make(map[string]struct{}, len(roles))
	for _, role := range roles {
		allowed[strings.ToLower(strings.TrimSpace(role))] = struct{}{}
	}
	return func(c *gin.Context) {
		userID := strings.TrimSpace(c.GetHeader("X-User-Id"))
		role := strings.ToLower(strings.TrimSpace(c.GetHeader("X-User-Role")))
		if !featureflags.SchedulingWriteAuthRequired() {
			if userID == "" {
				userID = "system"
			}
			if role == "" {
				role = "planner"
			}
			c.Set(ContextUserIDKey, userID)
			c.Set(ContextUserRoleKey, role)
			c.Next()
			return
		}
		if userID == "" || role == "" {
			c.AbortWithStatusJSON(http.StatusUnauthorized, dto.Response{Success: false, Error: "missing authenticated user or role"})
			return
		}
		c.Set(ContextUserIDKey, userID)
		c.Set(ContextUserRoleKey, role)
		if _, ok := allowed[role]; !ok {
			c.AbortWithStatusJSON(http.StatusForbidden, dto.Response{Success: false, Error: "insufficient role for this action"})
			return
		}
		c.Next()
	}
}
