package service

import (
	"testing"
	"time"

	"emas/internal/domain"
	"emas/internal/handler/dto"
	"emas/internal/repository"
	"emas/internal/testutil"
)

func TestJobCreateRollsBackWhenStepInsertFails(t *testing.T) {
	db := testutil.NewTestDB(t)
	process := domain.ProductProcess{
		ProcessID:   "PROC-P3-JOB",
		ProductID:   "PROD-P3-JOB",
		ProcessName: "Phase 3 rollback route",
		Version:     1,
		IsPrimary:   true,
	}
	step := domain.ProcessSteps{
		StepID:       "STEP-P3-JOB",
		ProcessID:    process.ProcessID,
		StepSequence: 1,
		StepName:     "Rollback step",
		StepType:     "cut",
	}
	if err := db.Create(&process).Error; err != nil {
		t.Fatalf("create process: %v", err)
	}
	if err := db.Create(&step).Error; err != nil {
		t.Fatalf("create process step: %v", err)
	}
	if err := db.Exec(`CREATE TRIGGER phase3_fail_job_step BEFORE INSERT ON job_steps BEGIN SELECT RAISE(FAIL, 'forced job step failure'); END;`).Error; err != nil {
		t.Fatalf("create trigger: %v", err)
	}
	defer db.Exec("DROP TRIGGER IF EXISTS phase3_fail_job_step")

	svc := NewJobService(
		repository.NewJobRepository(db),
		repository.NewJobStepRepository(db),
		repository.NewJobSlotRepository(db),
		repository.NewProcessRepository(db),
		repository.NewProductRepository(db),
		nil,
	)
	_, err := svc.Create(dto.CreateJobRequest{
		ProductID:     process.ProductID,
		QuantityTotal: 10,
		Deadline:      time.Now().Add(24 * time.Hour).Format(time.RFC3339),
	})
	if err == nil {
		t.Fatal("Create error = nil, want forced step insert failure")
	}

	var jobCount int64
	if err := db.Model(&domain.Job{}).Where("product_id = ?", process.ProductID).Count(&jobCount).Error; err != nil {
		t.Fatalf("count jobs: %v", err)
	}
	if jobCount != 0 {
		t.Fatalf("jobs persisted after failed create = %d, want 0", jobCount)
	}
}
