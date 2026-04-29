package service

import (
	"emas/internal/handler/dto"
	"net/url"
	"strconv"
	"strings"
)

type EndpointRoute struct {
	Path       string
	ParamsMeta map[string]QueryParamMeta
}

var queryRoutes = map[string]EndpointRoute{
	"machines":  {Path: "/api/v1/machines", ParamsMeta: extractQueryParamMeta(dto.MachineListQuery{})},
	"jobs":      {Path: "/api/v1/jobs", ParamsMeta: extractQueryParamMeta(dto.JobListQuery{})},
	"products":  {Path: "/api/v1/products", ParamsMeta: extractQueryParamMeta(dto.ProductListQuery{})},
	"inventory": {Path: "/api/v1/inventory/materials", ParamsMeta: extractQueryParamMeta(dto.InventoryMaterialsListQuery{})},
}

// ExecutableCall describes a full API call the frontend can execute directly.
type ExecutableCall struct {
	Method  string                 `json:"method"`
	Path    string                 `json:"path"`
	Body    map[string]interface{} `json:"body,omitempty"`
	Purpose string                 `json:"purpose"`
}

type IntentHandler interface {
	IntentName() string
	Resolve(ctx *intentResolverContext) ([]ExecutableCall, error)
}

var intentRegistry = map[string]IntentHandler{}

func RegisterIntentHandler(handler IntentHandler) {
	if handler == nil {
		return
	}
	intentRegistry[handler.IntentName()] = handler
}

func InitIntentRegistry() {
	intentRegistry = map[string]IntentHandler{}
	RegisterIntentHandler(&ProposeScheduleHandler{})
	RegisterIntentHandler(&ApproveProposalHandler{})
	RegisterIntentHandler(&RejectProposalHandler{})
	RegisterIntentHandler(&ApplyProposalHandler{})
	RegisterIntentHandler(&ScheduleAllJobsHandler{})
	RegisterIntentHandler(&ExplainJobHandler{})
	RegisterIntentHandler(&DelayRiskHandler{})
	RegisterIntentHandler(&MachineRankingHandler{})
	RegisterIntentHandler(&CreateJobHandler{})
	RegisterIntentHandler(&RescheduleJobHandler{})
	RegisterIntentHandler(&CancelJobHandler{})
	RegisterIntentHandler(&QueryStatusHandler{})
	RegisterIntentHandler(&ConsumeMaterialHandler{})
	RegisterIntentHandler(&ReceiveMaterialHandler{})
	RegisterIntentHandler(&RecordDowntimeHandler{})
	RegisterIntentHandler(&MaintenanceAlertsHandler{})
	RegisterIntentHandler(&ListProductsHandler{})
	RegisterIntentHandler(&HighRiskJobsHandler{})
	RegisterIntentHandler(&DashboardKPIsHandler{})
	RegisterIntentHandler(&GenerateReportHandler{})
	RegisterIntentHandler(&SplitStepHandler{})
}

func init() {
	InitIntentRegistry()
}

type intentResolverContext struct {
	base     string
	entities map[string]interface{}
}

func newIntentResolverContext(entities map[string]interface{}) *intentResolverContext {
	return &intentResolverContext{base: "/api/v1", entities: entities}
}

func (c *intentResolverContext) str(key string) string {
	if v, ok := c.entities[key]; ok {
		if s, ok := v.(string); ok {
			return s
		}
		if n, ok := v.(float64); ok {
			return strconv.FormatFloat(n, 'f', -1, 64)
		}
	}
	return ""
}

func (c *intentResolverContext) float(key string) float64 {
	if v, ok := c.entities[key]; ok {
		if f, ok := v.(float64); ok {
			return f
		}
		if s, ok := v.(string); ok {
			f, _ := strconv.ParseFloat(s, 64)
			return f
		}
	}
	return 0
}

func (c *intentResolverContext) int(key string) int {
	return int(c.float(key))
}

func buildQueryFromAccepted(basePath string, accepted map[string]string) string {
	u, err := url.Parse(basePath)
	if err != nil {
		return basePath
	}
	q := u.Query()
	for k, v := range accepted {
		q.Add(k, v)
	}
	u.RawQuery = q.Encode()
	return u.String()
}

func normalizeIntentHandlerKey(intent string) string {
	switch strings.ToLower(strings.TrimSpace(intent)) {
	case "reschedule_job":
		return "reschedule"
	case "cancel_job":
		return "cancel"
	default:
		return strings.ToLower(strings.TrimSpace(intent))
	}
}

// ResolveAction returns executable API calls for the given intent and entities.
func ResolveAction(intent string, entities map[string]interface{}) []ExecutableCall {
	key := normalizeIntentHandlerKey(intent)
	handler, ok := intentRegistry[key]
	if !ok {
		return nil
	}
	calls, err := handler.Resolve(newIntentResolverContext(entities))
	if err != nil {
		return nil
	}
	return calls
}
