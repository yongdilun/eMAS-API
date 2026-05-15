package service

import (
	"strings"
	"testing"
	"time"

	"emas/internal/domain"
	"emas/internal/handler/dto"
	"emas/internal/repository"
	"emas/internal/testutil"
)

func TestInventoryConsumeRejectsInsufficientStock(t *testing.T) {
	db := testutil.NewTestDB(t)
	repo := repository.NewInventoryRepository(db)
	material := &domain.InventoryMaterials{
		MaterialID:      "MAT-P3-LOW",
		MaterialName:    "Low stock material",
		Unit:            "kg",
		CurrentStock:    5,
		MinStock:        2,
		ReorderLevel:    10,
		StorageLocation: "RAW",
		Status:          domain.InventoryStatusInStock,
		LastUpdated:     time.Now(),
	}
	if err := repo.CreateMaterial(material); err != nil {
		t.Fatalf("create material: %v", err)
	}

	err := NewInventoryService(repo).ConsumeMaterial(dto.ConsumeMaterialRequest{
		MaterialID: material.MaterialID,
		Quantity:   6,
	})
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "insufficient stock") {
		t.Fatalf("ConsumeMaterial error = %v, want insufficient stock", err)
	}

	got, err := repo.GetMaterialByID(material.MaterialID)
	if err != nil {
		t.Fatalf("reload material: %v", err)
	}
	if got.CurrentStock != 5 {
		t.Fatalf("stock changed after rejected consume: got %.2f, want 5.00", got.CurrentStock)
	}
	var txCount int64
	if err := db.Model(&domain.InventoryTransactions{}).Where("material_id = ?", material.MaterialID).Count(&txCount).Error; err != nil {
		t.Fatalf("count transactions: %v", err)
	}
	if txCount != 0 {
		t.Fatalf("transactions after rejected consume = %d, want 0", txCount)
	}
}

func TestInventoryConsumeRollsBackStockWhenTransactionInsertFails(t *testing.T) {
	db := testutil.NewTestDB(t)
	repo := repository.NewInventoryRepository(db)
	material := &domain.InventoryMaterials{
		MaterialID:      "MAT-P3-ROLLBACK",
		MaterialName:    "Rollback material",
		Unit:            "kg",
		CurrentStock:    10,
		MinStock:        2,
		ReorderLevel:    10,
		StorageLocation: "RAW",
		Status:          domain.InventoryStatusInStock,
		LastUpdated:     time.Now(),
	}
	if err := repo.CreateMaterial(material); err != nil {
		t.Fatalf("create material: %v", err)
	}
	if err := db.Exec(`CREATE TRIGGER phase3_fail_inventory_transaction BEFORE INSERT ON inventory_transactions BEGIN SELECT RAISE(FAIL, 'forced inventory transaction failure'); END;`).Error; err != nil {
		t.Fatalf("create trigger: %v", err)
	}
	defer db.Exec("DROP TRIGGER IF EXISTS phase3_fail_inventory_transaction")

	err := NewInventoryService(repo).ConsumeMaterial(dto.ConsumeMaterialRequest{
		MaterialID: material.MaterialID,
		Quantity:   4,
	})
	if err == nil {
		t.Fatal("ConsumeMaterial error = nil, want forced insert failure")
	}

	got, err := repo.GetMaterialByID(material.MaterialID)
	if err != nil {
		t.Fatalf("reload material: %v", err)
	}
	if got.CurrentStock != 10 {
		t.Fatalf("stock after failed transaction insert = %.2f, want 10.00", got.CurrentStock)
	}
}
