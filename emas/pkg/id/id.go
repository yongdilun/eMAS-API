package id

import "github.com/google/uuid"

const (
	PrefixAIProposal      = "AIPROP-"
	PrefixApproval        = "CHAPPR-"
	PrefixExpectedArrival = "ARR-"
	PrefixFormula         = "F-"
	PrefixInventory       = "MAT-"
	PrefixJob             = "JOB-"
	PrefixJobStep         = "JS-"
	PrefixMachine         = "M-"
	PrefixProcess         = "PRC-"
	PrefixProcessStep     = "STP-"
	PrefixProduct         = "P-"
	PrefixSlot            = "SLOT-"
)

type Pattern struct {
	Entity string
	Field  string
	Prefix string
	Regex  string
}

var Patterns = []Pattern{
	{Entity: "proposal", Field: "proposal_id", Prefix: PrefixAIProposal, Regex: "^AIPROP-[A-Za-z0-9-]+$"},
	{Entity: "approval", Field: "approval_id", Prefix: PrefixApproval, Regex: "^CHAPPR-[A-Za-z0-9-]+$"},
	{Entity: "arrival", Field: "arrival_id", Prefix: PrefixExpectedArrival, Regex: "^ARR-[A-Za-z0-9-]+$"},
	{Entity: "formula", Field: "formula_id", Prefix: PrefixFormula, Regex: "^F-[A-Za-z0-9-]+$"},
	{Entity: "inventory", Field: "material_id", Prefix: PrefixInventory, Regex: "^MAT-[A-Za-z0-9-]+$"},
	{Entity: "job", Field: "job_id", Prefix: PrefixJob, Regex: "^JOB-[A-Za-z0-9-]+$"},
	{Entity: "step", Field: "job_step_id", Prefix: PrefixJobStep, Regex: "^JS-[A-Za-z0-9-]+$"},
	{Entity: "machine", Field: "machine_id", Prefix: PrefixMachine, Regex: "^M-[A-Za-z0-9-]+$"},
	{Entity: "process", Field: "process_id", Prefix: PrefixProcess, Regex: "^PRC-[A-Za-z0-9-]+$"},
	{Entity: "step", Field: "step_id", Prefix: PrefixProcessStep, Regex: "^STP-[A-Za-z0-9-]+$"},
	{Entity: "product", Field: "product_id", Prefix: PrefixProduct, Regex: "^P-[A-Za-z0-9-]+$"},
	{Entity: "slot", Field: "slot_id", Prefix: PrefixSlot, Regex: "^SLOT-[A-Za-z0-9-]+$"},
}

// New returns a new UUID string
func New() string {
	return uuid.New().String()
}

// NewPrefixed returns ID with prefix (e.g. "JOB-", "SLOT-")
func NewPrefixed(prefix string) string {
	return prefix + uuid.New().String()[:8]
}
