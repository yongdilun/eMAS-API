package service

type ConsumeMaterialHandler struct{}

func (h *ConsumeMaterialHandler) IntentName() string { return "consume_material" }
func (h *ConsumeMaterialHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	mat := ctx.str("material")
	if mat == "" {
		mat = ctx.str("material_id")
	}
	qty := ctx.float("quantity")
	if mat != "" && qty > 0 {
		body := map[string]interface{}{"material_id": mat, "quantity": qty}
		if j := ctx.str("job_id"); j != "" {
			body["reference_job_id"] = j
		}
		return []ExecutableCall{{Method: "POST", Path: ctx.base + "/inventory/consume", Body: body, Purpose: "Consume material."}}, nil
	}
	return nil, nil
}

type ReceiveMaterialHandler struct{}

func (h *ReceiveMaterialHandler) IntentName() string { return "receive_material" }
func (h *ReceiveMaterialHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	mat := ctx.str("material_id")
	if mat == "" {
		mat = ctx.str("material")
	}
	qty := ctx.float("quantity")
	if mat != "" && qty > 0 {
		return []ExecutableCall{{
			Method:  "POST",
			Path:    ctx.base + "/inventory/receive",
			Body:    map[string]interface{}{"material_id": mat, "quantity": qty},
			Purpose: "Receive material into inventory.",
		}}, nil
	}
	return nil, nil
}

type RecordDowntimeHandler struct{}

func (h *RecordDowntimeHandler) IntentName() string { return "record_downtime" }
func (h *RecordDowntimeHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	if m := ctx.str("machine_id"); m != "" {
		body := map[string]interface{}{"machine_id": m}
		if c := ctx.str("cause"); c != "" {
			body["cause"] = c
		}
		return []ExecutableCall{{Method: "POST", Path: ctx.base + "/machines/downtime", Body: body, Purpose: "Record machine downtime."}}, nil
	}
	return nil, nil
}

type MaintenanceAlertsHandler struct{}

func (h *MaintenanceAlertsHandler) IntentName() string { return "maintenance_alerts" }
func (h *MaintenanceAlertsHandler) Resolve(ctx *intentResolverContext) ([]ExecutableCall, error) {
	return []ExecutableCall{{Method: "GET", Path: ctx.base + "/machines/maintenance-alerts", Purpose: "Maintenance alerts."}}, nil
}
