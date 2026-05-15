package service

import (
	"emas/internal/domain"
	"emas/internal/repository"
	"emas/internal/testutil"
	"strings"
	"testing"
	"time"
)

func Test_settingsWorkWindows_ExcludesNonWorkday(t *testing.T) {
	db := testutil.NewTestDB(t)
	settingsRepo := repository.NewSystemSettingsRepository(db)
	_ = settingsRepo.PutString("scheduling.work_start_time", "08:00")
	_ = settingsRepo.PutString("scheduling.work_end_time", "17:00")
	_ = settingsRepo.PutString("scheduling.work_days", "1,2,3,4,5")

	svc := &SchedulingService{settingsRepo: settingsRepo}
	// Sunday in local time.
	from := time.Date(2026, 3, 29, 0, 0, 0, 0, time.Local)
	to := from.Add(24 * time.Hour)
	windows := svc.settingsWorkWindows(from, to)
	if len(windows) != 0 {
		t.Fatalf("expected no work windows on non-workday, got %d", len(windows))
	}
}

func Test_machineWorkWindows_IntersectsWithGlobalHoliday(t *testing.T) {
	db := testutil.NewTestDB(t)
	machineRepo := repository.NewMachineRepository(db)
	settingsRepo := repository.NewSystemSettingsRepository(db)

	holidayDate := "2026-04-01"
	_ = settingsRepo.PutString("scheduling.work_start_time", "08:00")
	_ = settingsRepo.PutString("scheduling.work_end_time", "17:00")
	_ = settingsRepo.PutString("scheduling.work_days", "0,1,2,3,4,5,6")
	_ = settingsRepo.PutString("scheduling.public_holidays", "[\""+holidayDate+"\"]")

	m := &domain.Machine{
		MachineID:       "M-CAL-01",
		MachineName:     "Calendar Test Machine",
		MachineType:     "CNC",
		Status:          domain.MachineStatusIdle,
		CapacityPerHour: 10,
	}
	if err := machineRepo.Create(m); err != nil {
		t.Fatalf("create machine: %v", err)
	}
	workStart := time.Date(2026, 4, 1, 8, 0, 0, 0, time.Local)
	workEnd := time.Date(2026, 4, 1, 17, 0, 0, 0, time.Local)
	if err := machineRepo.CreateCalendar(domain.MachineCalendar{
		CalendarID:       "MCAL-1",
		MachineID:        m.MachineID,
		StartTime:        workStart,
		EndTime:          workEnd,
		AvailabilityType: "work",
		ShiftName:        "A",
	}); err != nil {
		t.Fatalf("create machine calendar: %v", err)
	}

	svc := &SchedulingService{machineRepo: machineRepo, settingsRepo: settingsRepo}
	windows := svc.machineWorkWindows(m.MachineID, workStart, workEnd)
	if len(windows) != 0 {
		t.Fatalf("expected zero windows due to global holiday intersection, got %d", len(windows))
	}
}

func TestValidateSlotRejectsOverlapDowntimeMaintenanceAndCalendarRegression(t *testing.T) {
	db := testutil.NewTestDB(t)
	machineRepo := repository.NewMachineRepository(db)
	capRepo := repository.NewMachineCapabilityRepository(db)
	processRepo := repository.NewProcessRepository(db)
	jobRepo := repository.NewJobRepository(db)
	stepRepo := repository.NewJobStepRepository(db)
	slotRepo := repository.NewJobSlotRepository(db)
	downtimeRepo := repository.NewMachineDowntimeRepository(db)
	maintenanceRepo := repository.NewMaintenanceRepository(db)
	settingsRepo := repository.NewSystemSettingsRepository(db)

	if err := settingsRepo.PutString("scheduling.work_start_time", "08:00"); err != nil {
		t.Fatalf("set work start: %v", err)
	}
	if err := settingsRepo.PutString("scheduling.work_end_time", "17:00"); err != nil {
		t.Fatalf("set work end: %v", err)
	}
	if err := settingsRepo.PutString("scheduling.work_days", "1,2,3,4,5"); err != nil {
		t.Fatalf("set work days: %v", err)
	}

	process := domain.ProductProcess{ProcessID: "PROC-P3-SCHED", ProductID: "PROD-P3-SCHED", ProcessName: "Scheduling regression", Version: 1, IsPrimary: true}
	processStep := domain.ProcessSteps{StepID: "STEP-P3-SCHED", ProcessID: process.ProcessID, StepSequence: 1, StepName: "Cut", StepType: "cut", MachineTypeRequired: "CNC"}
	machine := domain.Machine{MachineID: "M-P3-SCHED", MachineName: "Phase 3 scheduler", MachineType: "CNC", Status: domain.MachineStatusIdle, CapacityPerHour: 10}
	job := domain.Job{JobID: "JOB-P3-SCHED", ProductID: process.ProductID, QuantityTotal: 10, Priority: domain.JobPriorityMedium, Deadline: time.Now().Add(24 * time.Hour), Status: domain.JobStatusScheduled, CreatedAt: time.Now(), UpdatedAt: time.Now()}
	jobStep := domain.JobSteps{JobStepID: "JSTEP-P3-SCHED", JobID: job.JobID, StepID: processStep.StepID, StepSequence: 1, QuantityTarget: 10, Status: domain.JobStepStatusScheduled}
	if err := processRepo.Create(&process); err != nil {
		t.Fatalf("create process: %v", err)
	}
	if err := processRepo.CreateStep(&processStep); err != nil {
		t.Fatalf("create process step: %v", err)
	}
	if err := machineRepo.Create(&machine); err != nil {
		t.Fatalf("create machine: %v", err)
	}
	if err := capRepo.Create(&domain.MachineCapabilities{CapabilityID: "CAP-P3-SCHED", MachineID: machine.MachineID, StepID: processStep.StepID, EfficiencyFactor: 1}); err != nil {
		t.Fatalf("create capability: %v", err)
	}
	if err := jobRepo.Create(&job); err != nil {
		t.Fatalf("create job: %v", err)
	}
	if err := stepRepo.Create(&jobStep); err != nil {
		t.Fatalf("create job step: %v", err)
	}

	day := time.Date(2026, 5, 18, 0, 0, 0, 0, time.Local)
	if err := machineRepo.CreateCalendar(domain.MachineCalendar{CalendarID: "MCAL-P3-WORK", MachineID: machine.MachineID, StartTime: day.Add(8 * time.Hour), EndTime: day.Add(12 * time.Hour), AvailabilityType: "work", ShiftName: "A"}); err != nil {
		t.Fatalf("create work calendar: %v", err)
	}
	if err := slotRepo.Create(&domain.JobStepScheduleSlots{SlotID: "SLOT-P3-EXISTING", JobStepID: jobStep.JobStepID, MachineID: machine.MachineID, ScheduledStart: day.Add(9 * time.Hour), ScheduledEnd: day.Add(10 * time.Hour), QuantityPlanned: 3, Status: domain.SlotStatusPlanned}); err != nil {
		t.Fatalf("create existing slot: %v", err)
	}
	if err := downtimeRepo.Create(&domain.MachineDowntime{DowntimeID: "DT-P3-SCHED", MachineID: machine.MachineID, Cause: "calibration", StartTime: day.Add(10 * time.Hour), EndTime: day.Add(11 * time.Hour), DurationMinutes: 60}); err != nil {
		t.Fatalf("create downtime: %v", err)
	}
	if err := maintenanceRepo.Create(&domain.MaintenanceRecords{MaintenanceID: "MNT-P3-SCHED", MachineID: machine.MachineID, MaintenanceType: domain.MaintenanceTypePreventive, StartTime: day.Add(11 * time.Hour), EndTime: day.Add(12 * time.Hour), Technician: "qa"}); err != nil {
		t.Fatalf("create maintenance: %v", err)
	}

	svc := NewSchedulingService(nil, nil, nil, processRepo, jobRepo, stepRepo, slotRepo, machineRepo, capRepo, downtimeRepo, maintenanceRepo, nil, nil, nil, nil, nil, nil, nil, nil, settingsRepo)
	tests := []struct {
		name       string
		start      time.Time
		end        time.Time
		wantReason string
	}{
		{name: "slot overlap", start: day.Add(9*time.Hour + 30*time.Minute), end: day.Add(10*time.Hour + 30*time.Minute), wantReason: "overlapping slots"},
		{name: "downtime overlap", start: day.Add(10*time.Hour + 30*time.Minute), end: day.Add(11 * time.Hour), wantReason: "machine downtime"},
		{name: "maintenance overlap", start: day.Add(11*time.Hour + 30*time.Minute), end: day.Add(12 * time.Hour), wantReason: "maintenance"},
		{name: "outside machine calendar", start: day.Add(12 * time.Hour), end: day.Add(13 * time.Hour), wantReason: "outside machine work calendar"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := svc.ValidateSlotWithOptions(jobStep.JobStepID, machine.MachineID, tt.start, tt.end, 1, "", SlotValidationOptions{IgnoreMinSplitQty: true})
			if err != nil {
				t.Fatalf("ValidateSlotWithOptions error: %v", err)
			}
			if result.Valid {
				t.Fatalf("slot validation valid=true, want false")
			}
			if !phase3ReasonsContain(result.Reasons, tt.wantReason) {
				t.Fatalf("reasons = %#v, want substring %q", result.Reasons, tt.wantReason)
			}
		})
	}
}

func phase3ReasonsContain(reasons []string, want string) bool {
	want = strings.ToLower(want)
	for _, reason := range reasons {
		if strings.Contains(strings.ToLower(reason), want) {
			return true
		}
	}
	return false
}
