package handler

import (
	"emas/internal/apperror"
	"emas/internal/handler/dto"
	"errors"
	"net/http"

	"github.com/gin-gonic/gin"
	"gorm.io/gorm"
)

func respondError(c *gin.Context, err error) {
	c.JSON(statusForError(err), dto.Response{Success: false, Error: err.Error()})
}

func statusForError(err error) int {
	if err == nil {
		return http.StatusInternalServerError
	}
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return http.StatusNotFound
	}
	kind, ok := apperror.KindOf(err)
	if !ok {
		return http.StatusInternalServerError
	}
	switch kind {
	case apperror.KindValidation:
		return http.StatusUnprocessableEntity
	case apperror.KindNotFound:
		return http.StatusNotFound
	case apperror.KindConflict:
		return http.StatusConflict
	case apperror.KindForbidden:
		return http.StatusForbidden
	default:
		return http.StatusInternalServerError
	}
}
