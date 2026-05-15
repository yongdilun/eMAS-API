package router

import (
	"encoding/json"
	"os"
	"sort"
	"strings"
	"testing"

	"emas/internal/testutil"
)

type swaggerDoc struct {
	BasePath string                            `json:"basePath"`
	Paths    map[string]map[string]interface{} `json:"paths"`
}

func TestRegisteredRoutesMatchSwagger(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := Setup(db)

	swaggerBytes, err := os.ReadFile("../../docs/swagger.json")
	if err != nil {
		t.Fatalf("read swagger.json: %v", err)
	}

	var doc swaggerDoc
	if err := json.Unmarshal(swaggerBytes, &doc); err != nil {
		t.Fatalf("parse swagger.json: %v", err)
	}
	if doc.BasePath == "" {
		t.Fatal("swagger basePath is empty")
	}

	actual := map[string]struct{}{}
	for _, route := range r.Routes() {
		if !strings.HasPrefix(route.Path, doc.BasePath+"/") {
			continue
		}
		actual[routeKey(route.Method, normalizeGinPath(strings.TrimPrefix(route.Path, doc.BasePath)))] = struct{}{}
	}

	documented := map[string]struct{}{}
	for path, operations := range doc.Paths {
		for method := range operations {
			if isHTTPMethod(method) {
				documented[routeKey(method, path)] = struct{}{}
			}
		}
	}

	missingFromSwagger := difference(actual, documented)
	extraInSwagger := difference(documented, actual)
	if len(missingFromSwagger) > 0 || len(extraInSwagger) > 0 {
		t.Fatalf("registered routes and swagger paths differ\nmissing from swagger:\n%s\nextra in swagger:\n%s", formatRoutes(missingFromSwagger), formatRoutes(extraInSwagger))
	}
}

func normalizeGinPath(path string) string {
	parts := strings.Split(path, "/")
	for i, part := range parts {
		if strings.HasPrefix(part, ":") {
			parts[i] = "{" + strings.TrimPrefix(part, ":") + "}"
		}
	}
	return strings.Join(parts, "/")
}

func routeKey(method, path string) string {
	return strings.ToUpper(method) + " " + path
}

func isHTTPMethod(method string) bool {
	switch strings.ToUpper(method) {
	case "GET", "POST", "PUT", "PATCH", "DELETE":
		return true
	default:
		return false
	}
}

func difference(left, right map[string]struct{}) []string {
	var out []string
	for key := range left {
		if _, ok := right[key]; !ok {
			out = append(out, key)
		}
	}
	sort.Strings(out)
	return out
}

func formatRoutes(routes []string) string {
	if len(routes) == 0 {
		return "  (none)"
	}
	return "  " + strings.Join(routes, "\n  ")
}
