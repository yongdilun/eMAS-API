package handler_test

func plannerAuthHeaders() map[string]string {
	return map[string]string{
		"X-User-Id":   "test-planner",
		"X-User-Role": "planner",
	}
}
