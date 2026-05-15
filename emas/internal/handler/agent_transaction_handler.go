package handler

import (
	"errors"
	"net/http"

	"emas/internal/handler/dto"
	"emas/internal/service"

	"github.com/gin-gonic/gin"
)

type AgentTransactionHandler struct {
	service *service.AgentTransactionService
}

func NewAgentTransactionHandler(service *service.AgentTransactionService) *AgentTransactionHandler {
	return &AgentTransactionHandler{service: service}
}

// @Summary Dry run an agent transaction bundle
// @Description Validate an agent transaction bundle without committing changes
// @Tags agent transaction
// @Accept json
// @Produce json
// @Param request body service.AgentTransactionRequest true "Agent Transaction Request"
// @Success 200 {object} dto.Response{data=service.AgentTransactionResult}
// @Failure 400 {object} dto.Response
// @Failure 409 {object} dto.Response
// @Failure 422 {object} dto.Response
// @Failure 500 {object} dto.Response
// @Router /agent/transaction/bundle-dry-run [post]
func (h *AgentTransactionHandler) BundleDryRun(c *gin.Context) {
	var req service.AgentTransactionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, dto.Response{Success: false, Error: err.Error()})
		return
	}
	result, err := h.service.DryRun(req)
	if err != nil {
		status, msg := agentTransactionStatus(err)
		c.JSON(status, dto.Response{Success: false, Error: msg})
		return
	}
	c.JSON(http.StatusOK, dto.Response{Success: true, Data: result})
}

// @Summary Commit an agent transaction bundle
// @Description Commit a validated agent transaction bundle
// @Tags agent transaction
// @Accept json
// @Produce json
// @Param Idempotency-Key header string false "Bundle idempotency key"
// @Param X-Bundle-Idempotency-Key header string false "Bundle idempotency key fallback"
// @Param request body service.AgentTransactionRequest true "Agent Transaction Request"
// @Success 200 {object} dto.Response{data=service.AgentTransactionResult}
// @Failure 400 {object} dto.Response
// @Failure 409 {object} dto.Response
// @Failure 422 {object} dto.Response
// @Failure 500 {object} dto.Response
// @Router /agent/transaction/commit [post]
func (h *AgentTransactionHandler) Commit(c *gin.Context) {
	var req service.AgentTransactionRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, dto.Response{Success: false, Error: err.Error()})
		return
	}
	bundleKey := c.GetHeader("Idempotency-Key")
	if bundleKey == "" {
		bundleKey = c.GetHeader("X-Bundle-Idempotency-Key")
	}
	result, err := h.service.Commit(req, bundleKey)
	if err != nil {
		status, msg := agentTransactionStatus(err)
		c.JSON(status, dto.Response{Success: false, Error: msg})
		return
	}
	c.JSON(http.StatusOK, dto.Response{Success: true, Data: result})
}

func agentTransactionStatus(err error) (int, string) {
	var txErr *service.AgentTransactionError
	if errors.As(err, &txErr) {
		return txErr.StatusCode, txErr.Message
	}
	return http.StatusInternalServerError, err.Error()
}
