package repository

import "gorm.io/gorm"

func (r *InventoryRepository) Transaction(fn func(*InventoryRepository) error) error {
	return r.db.Transaction(func(tx *gorm.DB) error {
		return fn(NewInventoryRepository(tx))
	})
}

func (r *JobRepository) Transaction(fn func(*gorm.DB) error) error {
	return r.db.Transaction(fn)
}
