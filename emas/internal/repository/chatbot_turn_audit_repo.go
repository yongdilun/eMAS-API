package repository

import (
	"emas/internal/domain"

	"gorm.io/gorm"
)

type ChatbotTurnAuditRepository struct {
	db *gorm.DB
}

func NewChatbotTurnAuditRepository(db *gorm.DB) *ChatbotTurnAuditRepository {
	return &ChatbotTurnAuditRepository{db: db}
}

func (r *ChatbotTurnAuditRepository) Create(audit *domain.ChatbotTurnAudit) error {
	return r.db.Create(audit).Error
}

func (r *ChatbotTurnAuditRepository) Update(audit *domain.ChatbotTurnAudit) error {
	return r.db.Save(audit).Error
}

type ChatbotToolExecutionSnapshotRepository struct {
	db *gorm.DB
}

func NewChatbotToolExecutionSnapshotRepository(db *gorm.DB) *ChatbotToolExecutionSnapshotRepository {
	return &ChatbotToolExecutionSnapshotRepository{db: db}
}

func (r *ChatbotToolExecutionSnapshotRepository) Create(snapshot *domain.ChatbotToolExecutionSnapshot) error {
	return r.db.Create(snapshot).Error
}
