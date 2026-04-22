package domain

import "time"

// ChatbotTurnAudit stores one chatbot planning/execution attempt for a user turn.
type ChatbotTurnAudit struct {
	ID                 string    `gorm:"column:id;primaryKey;size:64" json:"id"`
	ConversationID     string    `gorm:"column:conversation_id;size:64;index;not null" json:"conversation_id"`
	RequestID          string    `gorm:"column:request_id;size:128;index" json:"request_id"`
	UserMessageID      string    `gorm:"column:user_message_id;size:64;index" json:"user_message_id"`
	AssistantMessageID string    `gorm:"column:assistant_message_id;size:64;index" json:"assistant_message_id"`
	PlannerName        string    `gorm:"column:planner_name;size:64;not null" json:"planner_name"`
	PlanJSON           string    `gorm:"column:plan_json;type:text" json:"plan_json"`
	SelectedToolsJSON  string    `gorm:"column:selected_tools_json;type:text" json:"selected_tools_json"`
	Status             string    `gorm:"column:status;size:32;index;not null" json:"status"`
	Error              string    `gorm:"column:error;type:text" json:"error,omitempty"`
	CreatedAt          time.Time `gorm:"column:created_at" json:"created_at"`
}

func (ChatbotTurnAudit) TableName() string { return "chatbot_turn_audits" }

// ChatbotToolExecutionSnapshot stores one read-only tool execution during a turn.
type ChatbotToolExecutionSnapshot struct {
	ID             string    `gorm:"column:id;primaryKey;size:64" json:"id"`
	TurnAuditID    string    `gorm:"column:turn_audit_id;size:64;index;not null" json:"turn_audit_id"`
	ConversationID string    `gorm:"column:conversation_id;size:64;index;not null" json:"conversation_id"`
	ToolName       string    `gorm:"column:tool_name;size:128;index;not null" json:"tool_name"`
	ToolVersion    int       `gorm:"column:tool_version" json:"tool_version"`
	SchemaVersion  int       `gorm:"column:schema_version" json:"schema_version"`
	InputJSON      string    `gorm:"column:input_json;type:text" json:"input_json"`
	OutputJSON     string    `gorm:"column:output_json;type:text" json:"output_json"`
	LatencyMs      int       `gorm:"column:latency_ms" json:"latency_ms"`
	Success        bool      `gorm:"column:success" json:"success"`
	Error          string    `gorm:"column:error;type:text" json:"error,omitempty"`
	CreatedAt      time.Time `gorm:"column:created_at" json:"created_at"`
}

func (ChatbotToolExecutionSnapshot) TableName() string { return "chatbot_tool_execution_snapshots" }
