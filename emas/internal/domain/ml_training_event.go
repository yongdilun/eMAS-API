package domain

import "time"

// MLTrainingEvent is the persistent source of truth for advisory ML training/export.
// One row represents one planned slot lineage, updated over time as execution outcomes arrive.
type MLTrainingEvent struct {
	LineageID   string  `gorm:"column:lineage_id;primaryKey;size:80" json:"lineage_id"`
	SlotID      *string `gorm:"column:slot_id;size:50;index" json:"slot_id,omitempty"`
	JobID       string  `gorm:"column:job_id;size:50;index;not null" json:"job_id"`
	JobStepID   string  `gorm:"column:job_step_id;size:50;index;not null" json:"job_step_id"`
	ProposalID  string  `gorm:"column:proposal_id;size:50;index" json:"proposal_id"`
	ProductID   string  `gorm:"column:product_id;size:50;index;not null" json:"product_id"`
	StepID      string  `gorm:"column:step_id;size:50;index;not null" json:"step_id"`
	MachineID   string  `gorm:"column:machine_id;size:50;index;not null" json:"machine_id"`
	MachineType string  `gorm:"column:machine_type;size:100" json:"machine_type"`

	ProposalStatus         string  `gorm:"column:proposal_status;size:20" json:"proposal_status"`
	ProposalEngine         string  `gorm:"column:proposal_engine;size:50" json:"proposal_engine"`
	ProposalObjectiveScore float64 `gorm:"column:proposal_objective_score" json:"proposal_objective_score"`
	ProposalRolloutState   string  `gorm:"column:proposal_rollout_state;size:40" json:"proposal_rollout_state"`

	JobPriority          string     `gorm:"column:job_priority;size:20" json:"job_priority"`
	JobDeadline          time.Time  `gorm:"column:job_deadline" json:"job_deadline"`
	JobQuantityTotal     int        `gorm:"column:job_quantity_total" json:"job_quantity_total"`
	JobQuantityCompleted int        `gorm:"column:job_quantity_completed" json:"job_quantity_completed"`
	CanStartNow          bool       `gorm:"column:can_start_now" json:"can_start_now"`
	EarliestReadyAt      *time.Time `gorm:"column:earliest_ready_at" json:"earliest_ready_at,omitempty"`

	MaterialShortageCount   int     `gorm:"column:material_shortage_count" json:"material_shortage_count"`
	SubProductShortageCount int     `gorm:"column:sub_product_shortage_count" json:"sub_product_shortage_count"`
	TotalMaterialDemand     float64 `gorm:"column:total_material_demand" json:"total_material_demand"`
	TotalSubProductDemand   float64 `gorm:"column:total_sub_product_demand" json:"total_sub_product_demand"`
	ProductNestingDepth     int     `gorm:"column:product_nesting_depth" json:"product_nesting_depth"`

	StepSequence           int    `gorm:"column:step_sequence" json:"step_sequence"`
	StepType               string `gorm:"column:step_type;size:50" json:"step_type"`
	MachineTypeRequired    string `gorm:"column:machine_type_required;size:100" json:"machine_type_required"`
	AllowParallelExecution bool   `gorm:"column:allow_parallel_execution" json:"allow_parallel_execution"`
	MaxParallelMachines    int    `gorm:"column:max_parallel_machines" json:"max_parallel_machines"`
	MinSplitQty            int    `gorm:"column:min_split_qty" json:"min_split_qty"`
	TransferBatchSize      int    `gorm:"column:transfer_batch_size" json:"transfer_batch_size"`

	MachineStatus           string  `gorm:"column:machine_status;size:20" json:"machine_status"`
	MachineCapacityPerHour  int     `gorm:"column:machine_capacity_per_hour" json:"machine_capacity_per_hour"`
	MachineUtilizationRate  float64 `gorm:"column:machine_utilization_rate" json:"machine_utilization_rate"`
	MachineEfficiencyFactor float64 `gorm:"column:machine_efficiency_factor" json:"machine_efficiency_factor"`
	MachineHasCalendar      bool    `gorm:"column:machine_has_calendar" json:"machine_has_calendar"`
	MaintenanceDueInDays    int     `gorm:"column:maintenance_due_in_days" json:"maintenance_due_in_days"`

	SnapshotMachineIDsJSON       string `gorm:"column:snapshot_machine_ids_json;type:longtext" json:"-"`
	QueueLengthsVectorJSON       string `gorm:"column:queue_lengths_vector_json;type:longtext" json:"-"`
	MachineUtilizationVectorJSON string `gorm:"column:machine_utilization_vector_json;type:longtext" json:"-"`

	ScheduledStart      time.Time `gorm:"column:scheduled_start;index" json:"scheduled_start"`
	ScheduledEnd        time.Time `gorm:"column:scheduled_end" json:"scheduled_end"`
	PlannedDurationMins int       `gorm:"column:planned_duration_mins" json:"planned_duration_mins"`
	QuantityPlanned     int       `gorm:"column:quantity_planned" json:"quantity_planned"`
	AllocationPercent   float64   `gorm:"column:allocation_percent" json:"allocation_percent"`
	SplitGroupID        string    `gorm:"column:split_group_id;size:50;index" json:"split_group_id"`
	IsParallel          bool      `gorm:"column:is_parallel" json:"is_parallel"`
	BatchSequence       int       `gorm:"column:batch_sequence" json:"batch_sequence"`
	SlotStatus          string    `gorm:"column:slot_status;size:20" json:"slot_status"`

	ActualStart          *time.Time `gorm:"column:actual_start" json:"actual_start,omitempty"`
	ActualEnd            *time.Time `gorm:"column:actual_end" json:"actual_end,omitempty"`
	ActualDurationMins   int        `gorm:"column:actual_duration_mins" json:"actual_duration_mins"`
	DelayMinutes         int        `gorm:"column:delay_minutes" json:"delay_minutes"`
	ProducedQty          int        `gorm:"column:produced_qty" json:"produced_qty"`
	ScrapQty             int        `gorm:"column:scrap_qty" json:"scrap_qty"`
	CompletionRatio      float64    `gorm:"column:completion_ratio" json:"completion_ratio"`
	PlannedVsActualRatio float64    `gorm:"column:planned_vs_actual_ratio" json:"planned_vs_actual_ratio"`
	ScrapRate            float64    `gorm:"column:scrap_rate" json:"scrap_rate"`

	QueueWaitMinutes            int     `gorm:"column:queue_wait_minutes" json:"queue_wait_minutes"`
	QueueLenAtPlan              int     `gorm:"column:queue_len_at_plan" json:"queue_len_at_plan"`
	MaxQueueLen                 int     `gorm:"column:max_queue_len" json:"max_queue_len"`
	Util1h                      float64 `gorm:"column:util_1h" json:"util_1h"`
	Util8h                      float64 `gorm:"column:util_8h" json:"util_8h"`
	Util24h                     float64 `gorm:"column:util_24h" json:"util_24h"`
	Util7d                      float64 `gorm:"column:util_7d" json:"util_7d"`
	PrevProductIDOnMachine      string  `gorm:"column:prev_product_id_on_machine;size:50" json:"prev_product_id_on_machine"`
	SetupMinutesPrevChangeover  int     `gorm:"column:setup_minutes_prev_changeover" json:"setup_minutes_prev_changeover"`
	SameProductAsPrevMachineJob bool    `gorm:"column:same_product_as_prev_machine_job" json:"same_product_as_prev_machine_job"`
	ChangeoverCount24h          int     `gorm:"column:changeover_count_24h" json:"changeover_count_24h"`
	UpstreamLatenessMinutes     int     `gorm:"column:upstream_lateness_minutes" json:"upstream_lateness_minutes"`
	ReadinessDelayMinutes       int     `gorm:"column:readiness_delay_minutes" json:"readiness_delay_minutes"`

	DayOfWeek       int     `gorm:"column:day_of_week" json:"day_of_week"`
	ShiftName       string  `gorm:"column:shift_name;size:50" json:"shift_name"`
	IsHoliday       bool    `gorm:"column:is_holiday" json:"is_holiday"`
	IsNearHoliday   bool    `gorm:"column:is_near_holiday" json:"is_near_holiday"`
	IsWeekend       bool    `gorm:"column:is_weekend" json:"is_weekend"`
	HoursToShiftEnd float64 `gorm:"column:hours_to_shift_end" json:"hours_to_shift_end"`

	DatasetVersion    string     `gorm:"column:dataset_version;size:20" json:"dataset_version"`
	CapturedAt        time.Time  `gorm:"column:captured_at;index" json:"captured_at"`
	OutcomeRecordedAt *time.Time `gorm:"column:outcome_recorded_at;index" json:"outcome_recorded_at,omitempty"`
}

func (MLTrainingEvent) TableName() string { return "ml_training_events" }
