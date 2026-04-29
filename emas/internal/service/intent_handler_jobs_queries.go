package service

import "strings"

type CreateJobHandler struct{}

func (h *CreateJobHandler) IntentName() string { return "create_job" }
func (h *CreateJobHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	prod := ctx.str("product")
	if prod == "" {
		prod = ctx.str("product_id")
	}
	qty := ctx.int("quantity")
	if qty <= 0 {
		qty = 1
	}
	body := map[string]interface{}{"product_id": prod, "quantity_total": qty}
	if p := ctx.str("priority"); p != "" {
		body["priority"] = p
	}
	if d := ctx.str("deadline"); d != "" {
		body["deadline"] = d
	}
	return []ExecutableCall{{Method: "POST", Path: ctx.base + "/jobs", Body: body, Purpose: "Create job."}}, nil
}

type CancelJobHandler struct{}

func (h *CancelJobHandler) IntentName() string { return "cancel" }
func (h *CancelJobHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if j := ctx.str("job_id"); j != "" {
		return []ExecutableCall{{Method: "DELETE", Path: ctx.base + "/jobs/" + j, Purpose: "Cancel job."}}, nil
	}
	return nil, nil
}

type QueryStatusHandler struct{}

func (h *QueryStatusHandler) IntentName() string { return "query_status" }
func (h *QueryStatusHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	resource := strings.ToLower(ctx.str("resource"))
	switch resource {
	case "jobs":
		if j := ctx.str("job_id"); j != "" {
			return []ExecutableCall{
				{Method: "GET", Path: ctx.base + "/jobs/" + j, Purpose: "Job record."},
				{Method: "GET", Path: ctx.base + "/ai/scheduling/jobs/" + j + "/explanation", Purpose: "Job explanation."},
			}, nil
		}
		if route, ok := queryRoutes["jobs"]; ok {
			val := ValidateQueryEntities(ctx.entities, route.ParamsMeta)
			path := buildQueryFromAccepted(route.Path, val.AcceptedParams)
			return []ExecutableCall{{Method: "GET", Path: path, Purpose: "List jobs."}}, nil
		}
		return nil, nil
	default:
		if route, ok := queryRoutes[resource]; ok {
			val := ValidateQueryEntities(ctx.entities, route.ParamsMeta)
			path := buildQueryFromAccepted(route.Path, val.AcceptedParams)
			return []ExecutableCall{{Method: "GET", Path: path, Purpose: "List " + resource + "."}}, nil
		}
		return []ExecutableCall{
			{Method: "GET", Path: ctx.base + "/dashboard/kpis", Purpose: "Dashboard KPIs."},
			{Method: "GET", Path: ctx.base + "/alerts", Purpose: "Active alerts."},
		}, nil
	}
}
