package apperror

import (
	"errors"
	"fmt"
)

type Kind string

const (
	KindValidation Kind = "validation"
	KindNotFound   Kind = "not_found"
	KindConflict   Kind = "conflict"
	KindForbidden  Kind = "forbidden"
	KindInternal   Kind = "internal"
)

type Error struct {
	Kind    Kind
	Message string
	Err     error
}

func (e *Error) Error() string {
	if e == nil {
		return ""
	}
	if e.Message != "" {
		return e.Message
	}
	if e.Err != nil {
		return e.Err.Error()
	}
	return string(e.Kind)
}

func (e *Error) Unwrap() error {
	if e == nil {
		return nil
	}
	return e.Err
}

func New(kind Kind, message string) error {
	return &Error{Kind: kind, Message: message}
}

func Wrap(kind Kind, message string, err error) error {
	if err == nil {
		return New(kind, message)
	}
	return &Error{Kind: kind, Message: message, Err: err}
}

func Validation(message string) error { return New(KindValidation, message) }
func NotFound(message string) error   { return New(KindNotFound, message) }
func Conflict(message string) error   { return New(KindConflict, message) }
func Forbidden(message string) error  { return New(KindForbidden, message) }
func Internal(message string) error   { return New(KindInternal, message) }

func KindOf(err error) (Kind, bool) {
	var appErr *Error
	if errors.As(err, &appErr) && appErr != nil {
		return appErr.Kind, true
	}
	return "", false
}

func IsKind(err error, kind Kind) bool {
	got, ok := KindOf(err)
	return ok && got == kind
}

func Wrapf(kind Kind, err error, format string, args ...interface{}) error {
	return Wrap(kind, fmt.Sprintf(format, args...), err)
}
