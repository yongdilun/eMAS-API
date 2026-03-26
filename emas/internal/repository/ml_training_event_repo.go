package repository

import (
	"emas/internal/domain"
	"time"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
)

type MLTrainingDatasetStats struct {
	TotalRows               int64      `json:"total_rows"`
	OutcomeRows             int64      `json:"outcome_rows"`
	LatestCapturedAt        *time.Time `json:"latest_captured_at,omitempty"`
	LatestOutcomeRecordedAt *time.Time `json:"latest_outcome_recorded_at,omitempty"`
	OutcomeRowsSince        int64      `json:"outcome_rows_since,omitempty"`
}

type MLTrainingEventRepository struct {
	db *gorm.DB
}

func NewMLTrainingEventRepository(db *gorm.DB) *MLTrainingEventRepository {
	return &MLTrainingEventRepository{db: db}
}

func (r *MLTrainingEventRepository) Upsert(event *domain.MLTrainingEvent) error {
	if event == nil {
		return nil
	}
	return r.db.Clauses(clause.OnConflict{
		Columns:   []clause.Column{{Name: "lineage_id"}},
		UpdateAll: true,
	}).Create(event).Error
}

func (r *MLTrainingEventRepository) GetByLineageID(lineageID string) (*domain.MLTrainingEvent, error) {
	var event domain.MLTrainingEvent
	if err := r.db.Where("lineage_id = ?", lineageID).First(&event).Error; err != nil {
		return nil, err
	}
	return &event, nil
}

func (r *MLTrainingEventRepository) GetBySlotID(slotID string) (*domain.MLTrainingEvent, error) {
	var event domain.MLTrainingEvent
	if err := r.db.Where("slot_id = ?", slotID).First(&event).Error; err != nil {
		return nil, err
	}
	return &event, nil
}

func (r *MLTrainingEventRepository) ListAll() ([]domain.MLTrainingEvent, error) {
	var events []domain.MLTrainingEvent
	err := r.db.Order("scheduled_start").Find(&events).Error
	return events, err
}

func (r *MLTrainingEventRepository) CountOutcomeRecordedSince(ts time.Time) (int64, error) {
	var count int64
	err := r.db.Model(&domain.MLTrainingEvent{}).
		Where("outcome_recorded_at IS NOT NULL AND outcome_recorded_at > ?", ts).
		Count(&count).Error
	return count, err
}

func (r *MLTrainingEventRepository) DeleteDraftByProposalID(proposalID string) error {
	if proposalID == "" {
		return nil
	}
	return r.db.Where("proposal_id = ? AND (slot_id IS NULL OR slot_id = '')", proposalID).
		Delete(&domain.MLTrainingEvent{}).Error
}

func (r *MLTrainingEventRepository) Stats(since *time.Time) (*MLTrainingDatasetStats, error) {
	stats := &MLTrainingDatasetStats{}
	if err := r.db.Model(&domain.MLTrainingEvent{}).Count(&stats.TotalRows).Error; err != nil {
		return nil, err
	}
	if err := r.db.Model(&domain.MLTrainingEvent{}).
		Where("outcome_recorded_at IS NOT NULL").
		Count(&stats.OutcomeRows).Error; err != nil {
		return nil, err
	}
	type timestamps struct {
		LatestCapturedAt        *time.Time `gorm:"column:latest_captured_at"`
		LatestOutcomeRecordedAt *time.Time `gorm:"column:latest_outcome_recorded_at"`
	}
	var ts timestamps
	if err := r.db.Model(&domain.MLTrainingEvent{}).
		Select("MAX(captured_at) AS latest_captured_at, MAX(outcome_recorded_at) AS latest_outcome_recorded_at").
		Scan(&ts).Error; err != nil {
		return nil, err
	}
	stats.LatestCapturedAt = ts.LatestCapturedAt
	stats.LatestOutcomeRecordedAt = ts.LatestOutcomeRecordedAt
	if since != nil {
		if err := r.db.Model(&domain.MLTrainingEvent{}).
			Where("outcome_recorded_at IS NOT NULL AND outcome_recorded_at > ?", *since).
			Count(&stats.OutcomeRowsSince).Error; err != nil {
			return nil, err
		}
	}
	return stats, nil
}
