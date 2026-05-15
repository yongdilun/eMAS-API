package service

import (
	"testing"
	"time"

	"emas/internal/domain"
	"emas/internal/handler/dto"
	"emas/internal/repository"
	"emas/internal/testutil"
)

func TestProductionLogRollsBackWhenStepUpdateFails(t *testing.T) {
	db := testutil.NewTestDB(t)
	now := time.Date(2026, 5, 18, 9, 0, 0, 0, time.Local)
	job := domain.Job{
		JobID:         "JOB-P3-PLOG",
		ProductID:     "PROD-P3-PLOG",
		QuantityTotal: 10,
		Priority:      domain.JobPriorityMedium,
		Deadline:      now.Add(24 * time.Hour),
		Status:        domain.JobStatusScheduled,
		CreatedAt:     now,
		UpdatedAt:     now,
	}
	step := domain.JobSteps{
		JobStepID:      "JSTEP-P3-PLOG",
		JobID:          job.JobID,
		StepID:         "STEP-P3-PLOG",
		StepSequence:   1,
		QuantityTarget: 10,
		Status:         domain.JobStepStatusScheduled,
	}
	slot := domain.JobStepScheduleSlots{
		SlotID:          "SLOT-P3-PLOG",
		JobStepID:       step.JobStepID,
		MachineID:       "M-P3-PLOG",
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
	if err := db.Exec(`CREATE TRIGGER phase3_fail_job_step_update BEFORE UPDATE ON job_steps BEGIN SELECT RAISE(FAIL, 'forced job step update failure'); END;`).Error; err != nil {
		t.Fatalf("create trigger: %v", err)
	}
	defer db.Exec("DROP TRIGGER IF EXISTS phase3_fail_job_step_update")

	svc := NewProductionLogService(
		db,
		repository.NewProductionLogRepository(db),
		repository.NewJobSlotRepository(db),
		repository.NewJobStepRepository(db),
		repository.NewJobRepository(db),
		nil,
		nil,
	)
	_, err := svc.LogProduction(dto.LogProductionRequest{
		SlotID:           slot.SlotID,
		StartTime:        now,
		EndTime:          now.Add(time.Hour),
		QuantityProduced: 5,
	})
	if err == nil {
		t.Fatal("LogProduction error = nil, want forced step update failure")
	}

	var logCount int64
	if err := db.Model(&domain.ProductionLogs{}).Where("slot_id = ?", slot.SlotID).Count(&logCount).Error; err != nil {
		t.Fatalf("count production logs: %v", err)
	}
	if logCount != 0 {
		t.Fatalf("production logs persisted after failed update = %d, want 0", logCount)
	}
	reloadedJob, err := repository.NewJobRepository(db).GetByID(job.JobID)
	if err != nil {
		t.Fatalf("reload job: %v", err)
	}
	if reloadedJob.QuantityCompleted != 0 || reloadedJob.Status != domain.JobStatusScheduled {
		t.Fatalf("job changed after rollback: completed=%d status=%s", reloadedJob.QuantityCompleted, reloadedJob.Status)
	}
}
