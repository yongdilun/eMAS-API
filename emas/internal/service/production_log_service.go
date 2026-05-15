package service

import (
	"emas/internal/domain"
	"emas/internal/handler/dto"
	"emas/internal/repository"
	"emas/pkg/id"
	"encoding/json"
	"time"

	"gorm.io/gorm"
)

type ProductionLogService struct {
	db             *gorm.DB
	logRepo        *repository.ProductionLogRepository
	slotRepo       *repository.JobSlotRepository
	stepRepo       *repository.JobStepRepository
	jobRepo        *repository.JobRepository
	proposalRepo   *repository.AIProposalRepository
	scheduling     *SchedulingService
	inventoryRepo  *repository.InventoryRepository
	wipRepo        *repository.WIPRepository
	psmRepo        *repository.ProcessStepMaterialRepository
	dependencyRepo *repository.JobDependencyRepository
}

func NewProductionLogService(
	db *gorm.DB,
	logRepo *repository.ProductionLogRepository,
	slotRepo *repository.JobSlotRepository,
	stepRepo *repository.JobStepRepository,
	jobRepo *repository.JobRepository,
	proposalRepo *repository.AIProposalRepository,
	scheduling *SchedulingService,
) *ProductionLogService {
	return &ProductionLogService{
		db:             db,
		logRepo:        logRepo,
		slotRepo:       slotRepo,
		stepRepo:       stepRepo,
		jobRepo:        jobRepo,
		proposalRepo:   proposalRepo,
		scheduling:     scheduling,
		inventoryRepo:  repository.NewInventoryRepository(db),
		wipRepo:        repository.NewWIPRepository(db),
		psmRepo:        repository.NewProcessStepMaterialRepository(db),
		dependencyRepo: repository.NewJobDependencyRepository(db),
	}
}

func (s *ProductionLogService) LogProduction(req dto.LogProductionRequest) (*domain.ProductionLogs, error) {
	var created *domain.ProductionLogs
	err := s.db.Transaction(func(tx *gorm.DB) error {
		var scheduling *SchedulingService
		if s.scheduling != nil {
			scheduling = s.scheduling.WithTransaction(tx)
		}
		txSvc := &ProductionLogService{
			db:             tx,
			logRepo:        repository.NewProductionLogRepository(tx),
			slotRepo:       repository.NewJobSlotRepository(tx),
			stepRepo:       repository.NewJobStepRepository(tx),
			jobRepo:        repository.NewJobRepository(tx),
			proposalRepo:   repository.NewAIProposalRepository(tx),
			scheduling:     scheduling,
			inventoryRepo:  repository.NewInventoryRepository(tx),
			wipRepo:        repository.NewWIPRepository(tx),
			psmRepo:        repository.NewProcessStepMaterialRepository(tx),
			dependencyRepo: repository.NewJobDependencyRepository(tx),
		}
		pl, err := txSvc.logProduction(req)
		if err != nil {
			return err
		}
		created = pl
		return nil
	})
	if err != nil {
		return nil, err
	}
	return created, nil
}

func (s *ProductionLogService) logProduction(req dto.LogProductionRequest) (*domain.ProductionLogs, error) {
	pl := &domain.ProductionLogs{
		ProductionID:     id.NewPrefixed("PL-"),
		SlotID:           req.SlotID,
		StartTime:        req.StartTime,
		EndTime:          req.EndTime,
		QuantityProduced: req.QuantityProduced,
		QuantityScrap:    req.QuantityScrap,
		OperatorNotes:    req.OperatorNotes,
		DowntimeMinutes:  req.DowntimeMinutes,
	}
	if err := s.logRepo.Create(pl); err != nil {
		return nil, err
	}
	slot, err := s.slotRepo.GetByID(req.SlotID)
	if err != nil {
		return nil, err
	}
	step, err := s.stepRepo.GetByID(slot.JobStepID)
	if err != nil {
		return nil, err
	}
	if err := s.syncInventoryFromLog(slot, step, req); err != nil {
		return nil, err
	}
	step.QuantityCompleted += req.QuantityProduced
	if step.QuantityCompleted >= step.QuantityTarget {
		step.Status = domain.JobStepStatusCompleted
	} else if req.QuantityProduced+req.QuantityScrap < slot.QuantityPlanned {
		step.Status = domain.JobStepStatusBlocked
	} else if step.QuantityCompleted > 0 {
		step.Status = domain.JobStepStatusRunning
	}
	if err := s.stepRepo.Update(step); err != nil {
		return nil, err
	}
	job, err := s.jobRepo.GetByID(step.JobID)
	if err != nil {
		return nil, err
	}
	job.QuantityCompleted += req.QuantityProduced
	if job.QuantityCompleted >= job.QuantityTotal {
		job.Status = domain.JobStatusCompleted
	} else if req.QuantityProduced+req.QuantityScrap < slot.QuantityPlanned {
		job.Status = domain.JobStatusBlocked
	} else if job.QuantityCompleted > 0 {
		job.Status = domain.JobStatusRunning
	}
	if err := s.jobRepo.Update(job); err != nil {
		return nil, err
	}
	totalProduced, err := s.logRepo.SumProducedBySlotID(req.SlotID)
	if err != nil {
		return nil, err
	}
	if totalProduced >= slot.QuantityPlanned {
		slot.Status = domain.SlotStatusCompleted
	} else {
		slot.Status = domain.SlotStatusRunning
	}
	if err := s.slotRepo.Update(slot); err != nil {
		return nil, err
	}
	if slot.ProposalID != "" && s.proposalRepo != nil {
		if err := s.refreshProposalOutcome(slot.ProposalID); err != nil {
			return nil, err
		}
	}
	if s.scheduling != nil {
		if err := s.scheduling.CaptureMLTrainingEventForSlot(slot.SlotID); err != nil {
			return nil, err
		}
	}
	return pl, nil
}

func (s *ProductionLogService) syncInventoryFromLog(slot *domain.JobStepScheduleSlots, step *domain.JobSteps, req dto.LogProductionRequest) error {
	if slot == nil || step == nil || s.scheduling == nil || s.psmRepo == nil || s.inventoryRepo == nil {
		return nil
	}
	processStep, err := s.scheduling.GetProcessStepForJobStep(step.JobStepID)
	if err != nil || processStep == nil {
		return nil
	}
	inputs, err := s.psmRepo.ListInputsByStepID(processStep.StepID)
	if err != nil {
		return err
	}
	outputs, err := s.psmRepo.ListOutputsByStepID(processStep.StepID)
	if err != nil {
		return err
	}
	inputUnits := float64(req.QuantityProduced + req.QuantityScrap)
	outputUnits := float64(req.QuantityProduced)

	for _, input := range inputs {
		required := inputUnits * input.QuantityPerUnit
		if required <= 0 {
			continue
		}
		if input.ProductID != nil {
			productID := *input.ProductID
			wipConsumed, err := s.consumeWIP(step.JobID, productID, required)
			if err != nil {
				return err
			}
			remaining := required - wipConsumed
			if remaining > 0 {
				if err := s.consumePendingProductReservations(step.JobID, step.JobStepID, productID, remaining); err != nil {
					return err
				}
			}
			continue
		}
		if input.MaterialID != nil {
			if err := s.consumePendingMaterialReservations(step.JobID, step.JobStepID, *input.MaterialID, required); err != nil {
				return err
			}
		}
	}

	for _, output := range outputs {
		if output.ProductID == nil {
			continue
		}
		productID := *output.ProductID
		qty := outputUnits * output.QuantityPerUnit
		if qty <= 0 {
			continue
		}
		if s.outputStaysInWIP(step.JobID, processStep.StepSequence, productID) {
			if err := s.wipRepo.UpsertWIP(&domain.WIPInventory{
				ID:        id.NewPrefixed("WIP-"),
				JobStepID: step.JobStepID,
				ProductID: &productID,
				Quantity:  qty,
				Unit:      output.Unit,
				Location:  "WIP",
				UpdatedAt: time.Now().UTC(),
			}); err != nil {
				return err
			}
			continue
		}
		inventory := &domain.ProductInventory{
			InventoryID:      id.NewPrefixed("PINV-"),
			ProductID:        productID,
			QuantityOnHand:   qty,
			QuantityReserved: 0,
			Status:           domain.ProductInventoryStatusAvailable,
			StorageLocation:  "FG",
			AvailableFrom:    alignSuccessorStart(req.EndTime.UTC()),
			LastUpdated:      time.Now().UTC(),
		}
		if err := s.inventoryRepo.CreateProductInventory(inventory); err != nil {
			return err
		}
	}
	if req.QuantityProduced < slot.QuantityPlanned {
		if err := s.blockDependentConsumers(step.JobID, step.JobStepID); err != nil {
			return err
		}
	}
	return nil
}

func (s *ProductionLogService) consumeWIP(jobID, productID string, qty float64) (float64, error) {
	if s.wipRepo == nil || qty <= 0 {
		return 0, nil
	}
	items, err := s.wipRepo.ListWIPByJobID(jobID)
	if err != nil {
		return 0, err
	}
	consumed := 0.0
	for _, item := range items {
		if item.ProductID == nil || *item.ProductID != productID || item.Quantity <= 0 {
			continue
		}
		available := item.Quantity
		used := mathMinFloat(available, qty-consumed)
		if used <= 0 {
			continue
		}
		item.Quantity -= used
		item.UpdatedAt = time.Now().UTC()
		if err := s.wipRepo.UpsertWIP(&item); err != nil {
			return consumed, err
		}
		consumed += used
		if consumed >= qty {
			break
		}
	}
	return consumed, nil
}

func (s *ProductionLogService) consumePendingMaterialReservations(jobID, jobStepID, materialID string, qty float64) error {
	reservations, err := s.inventoryRepo.ListReservations(materialID, domain.InventoryReservationStatusPending)
	if err != nil {
		return err
	}
	return s.consumeMaterialReservations(reservations, jobID, jobStepID, qty)
}

func (s *ProductionLogService) consumeMaterialReservations(reservations []domain.InventoryReservation, jobID, jobStepID string, qty float64) error {
	remaining := qty
	for _, reservation := range reservations {
		if remaining <= 0 {
			break
		}
		if reservation.JobID != jobID || reservation.JobStepID != jobStepID || reservation.ReservedQty <= 0 {
			continue
		}
		used := mathMinFloat(reservation.ReservedQty, remaining)
		reservation.ReservedQty -= used
		reservation.UpdatedAt = time.Now().UTC()
		if reservation.ReservedQty <= 0 {
			reservation.Status = domain.InventoryReservationStatusConsumed
		}
		if err := s.inventoryRepo.UpdateReservation(&reservation); err != nil {
			return err
		}
		remaining -= used
	}
	return nil
}

func (s *ProductionLogService) consumePendingProductReservations(jobID, jobStepID, productID string, qty float64) error {
	reservations, err := s.inventoryRepo.ListProductReservations(productID, domain.InventoryReservationStatusPending)
	if err != nil {
		return err
	}
	remaining := qty
	for _, reservation := range reservations {
		if remaining <= 0 {
			break
		}
		if reservation.JobID != jobID || reservation.JobStepID != jobStepID || reservation.ReservedQty <= 0 {
			continue
		}
		used := mathMinFloat(reservation.ReservedQty, remaining)
		reservation.ReservedQty -= used
		reservation.UpdatedAt = time.Now().UTC()
		if reservation.ReservedQty <= 0 {
			reservation.Status = domain.InventoryReservationStatusConsumed
		}
		if err := s.inventoryRepo.UpdateProductReservation(&reservation); err != nil {
			return err
		}
		remaining -= used
	}
	return nil
}

func (s *ProductionLogService) outputStaysInWIP(jobID string, currentSequence int, productID string) bool {
	steps, err := s.stepRepo.ListByJobID(jobID)
	if err != nil {
		return false
	}
	for _, step := range steps {
		if step.StepSequence <= currentSequence {
			continue
		}
		processStep, err := s.scheduling.GetProcessStepForJobStep(step.JobStepID)
		if err != nil || processStep == nil {
			continue
		}
		inputs, err := s.psmRepo.ListInputsByStepID(processStep.StepID)
		if err != nil {
			continue
		}
		for _, input := range inputs {
			if input.ProductID != nil && *input.ProductID == productID {
				return true
			}
		}
	}
	return false
}

func (s *ProductionLogService) blockDependentConsumers(parentJobID, parentJobStepID string) error {
	if s.dependencyRepo == nil {
		return nil
	}
	deps, err := s.dependencyRepo.ListByConsumerJobStepID(parentJobStepID)
	if err != nil || len(deps) == 0 {
		deps, err = s.dependencyRepo.ListByParentJobID(parentJobID)
		if err != nil {
			return err
		}
	}
	for _, dep := range deps {
		step, err := s.stepRepo.GetByID(dep.ConsumerJobStepID)
		if err == nil && step != nil {
			step.Status = domain.JobStepStatusBlocked
			if err := s.stepRepo.Update(step); err != nil {
				return err
			}
			job, jobErr := s.jobRepo.GetByID(step.JobID)
			if jobErr == nil && job != nil {
				job.Status = domain.JobStatusBlocked
				job.UpdatedAt = time.Now().UTC()
				job.Notes = schedulerNoteAppend(job.Notes, "reason_code="+reasonCodeInsufficientOutput)
				if err := s.jobRepo.Update(job); err != nil {
					return err
				}
			}
		} else if err != nil {
			return err
		}
	}
	return nil
}

func mathMinFloat(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func (s *ProductionLogService) refreshProposalOutcome(proposalID string) error {
	proposal, err := s.proposalRepo.GetByID(proposalID)
	if err != nil {
		return err
	}
	slots, err := s.slotRepo.ListByProposalID(proposalID)
	if err != nil || len(slots) == 0 {
		return err
	}
	totalProduced := 0
	totalScrap := 0
	completedSlots := 0
	var actualCompletion *time.Time
	for _, slot := range slots {
		logs, err := s.logRepo.ListBySlotID(slot.SlotID)
		if err != nil {
			return err
		}
		for _, log := range logs {
			totalProduced += log.QuantityProduced
			totalScrap += log.QuantityScrap
			if actualCompletion == nil || log.EndTime.After(*actualCompletion) {
				end := log.EndTime
				actualCompletion = &end
			}
		}
		if slot.Status == domain.SlotStatusCompleted {
			completedSlots++
		}
	}
	outcome := map[string]interface{}{
		"proposal_id":          proposalID,
		"completed_slots":      completedSlots,
		"total_slots":          len(slots),
		"quantity_produced":    totalProduced,
		"quantity_scrap":       totalScrap,
		"actual_completion_at": actualCompletion,
	}
	estimateDeviation := 0
	if proposal.EstimatedCompletionAt != nil && actualCompletion != nil {
		estimateDeviation = int(actualCompletion.Sub(*proposal.EstimatedCompletionAt).Minutes())
		outcome["estimate_deviation_mins"] = estimateDeviation
	}
	raw, err := json.Marshal(outcome)
	if err != nil {
		return err
	}
	now := time.Now().UTC()
	proposal.OutcomeJSON = string(raw)
	proposal.ActualProducedQty = totalProduced
	proposal.ActualScrapQty = totalScrap
	proposal.ActualCompletionAt = actualCompletion
	proposal.EstimateDeviationMins = estimateDeviation
	if completedSlots >= len(slots) && len(slots) > 0 {
		proposal.OutcomeStatus = "completed"
	} else {
		proposal.OutcomeStatus = "in_progress"
	}
	proposal.LastOutcomeRecordedAt = &now
	proposal.UpdatedAt = now
	return s.proposalRepo.Update(proposal)
}
