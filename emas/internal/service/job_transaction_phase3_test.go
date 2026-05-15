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

func TestJobDeleteRollsBackWhenSlotDeleteFails(t *testing.T) {
	db := testutil.NewTestDB(t)
	now := time.Date(2026, 5, 18, 9, 0, 0, 0, time.UTC)
	job := domain.Job{
		JobID:         "JOB-P4-DELETE",
		ProductID:     "PROD-P4-DELETE",
		QuantityTotal: 10,
		Priority:      domain.JobPriorityMedium,
		Deadline:      now.Add(24 * time.Hour),
		Status:        domain.JobStatusScheduled,
		CreatedAt:     now,
		UpdatedAt:     now,
	}
	step := domain.JobSteps{
		JobStepID:      "JSTEP-P4-DELETE",
		JobID:          job.JobID,
		StepID:         "STEP-P4-DELETE",
		StepSequence:   1,
		QuantityTarget: 10,
		Status:         domain.JobStepStatusScheduled,
	}
	slot := domain.JobStepScheduleSlots{
		SlotID:          "SLOT-P4-DELETE",
		JobStepID:       step.JobStepID,
		MachineID:       "M-P4-DELETE",
		ScheduledStart:  now,
		ScheduledEnd:    now.Add(time.Hour),
		QuantityPlanned: 10,
		Status:          domain.SlotStatusPlanned,
	}
	if err := db.Create(&job).Error; err != nil {
		t.Fatalf("create job: %v", err)
	}
	if err := db.Create(&step).Error; err != nil {
		t.Fatalf("create step: %v", err)
	}
	if err := db.Create(&slot).Error; err != nil {
		t.Fatalf("create slot: %v", err)
	}
	if err := db.Exec(`CREATE TRIGGER phase4_fail_slot_delete BEFORE DELETE ON job_step_schedule_slots BEGIN SELECT RAISE(FAIL, 'forced slot delete failure'); END;`).Error; err != nil {
		t.Fatalf("create trigger: %v", err)
	}
	defer db.Exec("DROP TRIGGER IF EXISTS phase4_fail_slot_delete")

	svc := NewJobService(
		repository.NewJobRepository(db),
		repository.NewJobStepRepository(db),
		repository.NewJobSlotRepository(db),
		repository.NewProcessRepository(db),
		repository.NewProductRepository(db),
		nil,
	)
	if err := svc.Delete(job.JobID); err == nil {
		t.Fatal("Delete error = nil, want forced slot delete failure")
	}

	var jobCount, stepCount, slotCount int64
	if err := db.Model(&domain.Job{}).Where("job_id = ?", job.JobID).Count(&jobCount).Error; err != nil {
		t.Fatalf("count jobs: %v", err)
	}
	if err := db.Model(&domain.JobSteps{}).Where("job_step_id = ?", step.JobStepID).Count(&stepCount).Error; err != nil {
		t.Fatalf("count steps: %v", err)
	}
	if err := db.Model(&domain.JobStepScheduleSlots{}).Where("slot_id = ?", slot.SlotID).Count(&slotCount).Error; err != nil {
		t.Fatalf("count slots: %v", err)
	}
	if jobCount != 1 || stepCount != 1 || slotCount != 1 {
		t.Fatalf("delete rollback counts: jobs=%d steps=%d slots=%d, want all 1", jobCount, stepCount, slotCount)
	}
}
