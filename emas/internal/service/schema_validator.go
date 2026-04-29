package service

import (
	"fmt"
	"reflect"
	"strings"
)

type QueryParamMeta struct {
	Name          string
	AllowedValues []string // empty if no restrictions
	Description   string
}

func extractQueryParamMeta(model interface{}) map[string]QueryParamMeta {
	meta := make(map[string]QueryParamMeta)
	t := reflect.TypeOf(model)
	if t.Kind() == reflect.Ptr {
		t = t.Elem()
	}
	if t.Kind() != reflect.Struct {
		return meta
	}
	for i := 0; i < t.NumField(); i++ {
		field := t.Field(i)
		formTag := field.Tag.Get("form")
		if formTag == "" || formTag == "-" {
			continue
		}
		parts := strings.Split(formTag, ",")
		name := parts[0]
		if name == "" {
			continue
		}

		pm := QueryParamMeta{Name: name}

		// check binding
		bindingTag := field.Tag.Get("binding")
		if bindingTag != "" {
			bParts := strings.Split(bindingTag, ",")
			for _, b := range bParts {
				if strings.HasPrefix(b, "oneof=") {
					vals := strings.TrimPrefix(b, "oneof=")
					pm.AllowedValues = strings.Split(vals, " ")
				}
			}
		}
		// check enums tag if binding is missing
		if len(pm.AllowedValues) == 0 {
			enumsTag := field.Tag.Get("enums")
			if enumsTag != "" {
				pm.AllowedValues = strings.Split(enumsTag, ",")
			}
		}

		// check description (if any)
		if desc := field.Tag.Get("description"); desc != "" {
			pm.Description = desc
		}

		meta[name] = pm
	}
	return meta
}

type RejectedParam struct {
	Field         string
	RawValue      string
	Reason        string
	AllowedValues []string
}

type ValidationResult struct {
	AcceptedParams map[string]string
	RejectedParams []RejectedParam
}

// ValidateQueryEntities verifies NLP entities against the DTO metadata
func ValidateQueryEntities(entities map[string]interface{}, routeParams map[string]QueryParamMeta) ValidationResult {
	res := ValidationResult{
		AcceptedParams: make(map[string]string),
		RejectedParams: make([]RejectedParam, 0),
	}

	for k, v := range entities {
		// Ignore standard NLP routing keys
		if k == "resource" || k == "intent" || k == "action" {
			continue
		}

		strVal := fmt.Sprintf("%v", v)
		if strVal == "" {
			continue
		}

		meta, exists := routeParams[k]
		if !exists {
			res.RejectedParams = append(res.RejectedParams, RejectedParam{
				Field:    k,
				RawValue: strVal,
				Reason:   "Unsupported filter",
			})
			continue
		}

		if len(meta.AllowedValues) > 0 {
			valid := false
			for _, allowed := range meta.AllowedValues {
				if strVal == allowed {
					valid = true
					break
				}
			}
			if !valid {
				res.RejectedParams = append(res.RejectedParams, RejectedParam{
					Field:         k,
					RawValue:      strVal,
					Reason:        "Invalid value",
					AllowedValues: meta.AllowedValues,
				})
				continue
			}
		}

		res.AcceptedParams[k] = strVal
	}
	return res
}
