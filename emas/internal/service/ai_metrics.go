package service

import "sync"

type AIMetrics struct {
	mu                       sync.Mutex
	ProposalGenerated        int     `json:"proposal_generated"`
	ProposalApproved         int     `json:"proposal_approved"`
	ProposalRejected         int     `json:"proposal_rejected"`
	ProposalApplied          int     `json:"proposal_applied"`
	ProposalStale            int     `json:"proposal_stale"`
	ProposalApplyFailures    int     `json:"proposal_apply_failures"`
	ReadonlyExecutions       int     `json:"readonly_executions"`
	SolverExecutions         int     `json:"solver_executions"`
	HeuristicExecutions      int     `json:"heuristic_executions"`
	SolverFallbacks          int     `json:"solver_fallbacks"`
	SolverShadowSamples      int     `json:"solver_shadow_samples"`
	AcceptanceRate           float64 `json:"acceptance_rate"`
	AvgEstimateDeviationMins float64 `json:"avg_estimate_deviation_mins"`
	AvgScrapQty              float64 `json:"avg_scrap_qty"`
	MLPredictionSuccesses    int     `json:"ml_prediction_successes"`
	MLPredictionFailures     int     `json:"ml_prediction_failures"`
	MLLowConfidenceFallbacks int     `json:"ml_low_confidence_fallbacks"`
	MLAverageLatencyMs       float64 `json:"ml_average_latency_ms"`
	MLAverageFeatureCoverage float64 `json:"ml_average_feature_coverage"`
	RolloutState             string  `json:"rollout_state"`
	KpiGatePassed            bool    `json:"kpi_gate_passed"`

	mlLatencySamples         int `json:"-"`
	mlFeatureCoverageSamples int `json:"-"`
}

func NewAIMetrics() *AIMetrics {
	return &AIMetrics{}
}

func (m *AIMetrics) Snapshot() AIMetrics {
	m.mu.Lock()
	defer m.mu.Unlock()
	return *m
}

func (m *AIMetrics) Inc(field *int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	*field = *field + 1
}

func (m *AIMetrics) RecordMLSuccess(latencyMs, featureCoverage float64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.MLPredictionSuccesses++
	m.mlLatencySamples++
	m.MLAverageLatencyMs += (latencyMs - m.MLAverageLatencyMs) / float64(m.mlLatencySamples)
	m.mlFeatureCoverageSamples++
	m.MLAverageFeatureCoverage += (featureCoverage - m.MLAverageFeatureCoverage) / float64(m.mlFeatureCoverageSamples)
}

func (m *AIMetrics) RecordMLFailure() {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.MLPredictionFailures++
}

func (m *AIMetrics) RecordMLLowConfidenceFallback(latencyMs, featureCoverage float64) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.MLLowConfidenceFallbacks++
	m.mlLatencySamples++
	m.MLAverageLatencyMs += (latencyMs - m.MLAverageLatencyMs) / float64(m.mlLatencySamples)
	m.mlFeatureCoverageSamples++
	m.MLAverageFeatureCoverage += (featureCoverage - m.MLAverageFeatureCoverage) / float64(m.mlFeatureCoverageSamples)
}
