package service

import "strings"

type ListProductsHandler struct{}

func (h *ListProductsHandler) IntentName() string { return "list_products" }
func (h *ListProductsHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	return []ExecutableCall{{Method: "GET", Path: ctx.base + "/products", Purpose: "List products."}}, nil
}

type HighRiskJobsHandler struct{}

func (h *HighRiskJobsHandler) IntentName() string { return "high_risk_jobs" }
func (h *HighRiskJobsHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	return []ExecutableCall{{Method: "GET", Path: ctx.base + "/predictive/high-risk-jobs", Purpose: "High-risk jobs forecast."}}, nil
}

type DashboardKPIsHandler struct{}

func (h *DashboardKPIsHandler) IntentName() string { return "dashboard_kpis" }
func (h *DashboardKPIsHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	return []ExecutableCall{{Method: "GET", Path: ctx.base + "/dashboard/kpis", Purpose: "Dashboard KPIs."}}, nil
}

type GenerateReportHandler struct{}

func (h *GenerateReportHandler) IntentName() string { return "generate_report" }
func (h *GenerateReportHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	rt := strings.ToLower(ctx.str("report_type"))
	switch rt {
	case "bottleneck", "bottlenecks":
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/ai/scheduling/bottleneck-forecast", Purpose: "Bottleneck forecast."}}, nil
	case "utilization":
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/reports/machine-utilization", Purpose: "Machine utilization report."}}, nil
	case "oee":
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/reports/oee", Purpose: "OEE report."}}, nil
	case "completion", "job", "jobs":
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/reports/job-completion", Purpose: "Job completion report."}}, nil
	case "inventory":
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/reports/inventory-trends", Purpose: "Inventory trends."}}, nil
	case "quality":
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/reports/quality-trends", Purpose: "Quality trends."}}, nil
	case "maintenance":
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/reports/maintenance-efficiency", Purpose: "Maintenance efficiency."}}, nil
	default:
		return []ExecutableCall{{Method: "GET", Path: ctx.base + "/reports/production-output", Purpose: "Production output report."}}, nil
	}
}
