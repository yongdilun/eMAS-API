package handler_test

import (
	"net/http"
	"testing"

	"emas/internal/router"
	"emas/internal/testutil"
)

func TestInventoryHandler_CRUD(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	// Create material
	w := testutil.Request(r, "POST", "/api/v1/inventory/materials", map[string]interface{}{
		"material_id": "MAT-TEST", "material_name": "Aluminum", "current_stock": 100,
		"min_stock": 10, "reorder_level": 20, "unit": "kg",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create: got %d", w.Code)
	}

	// Get
	w = testutil.Request(r, "GET", "/api/v1/inventory/materials/MAT-TEST", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("get: got %d", w.Code)
	}

	// List
	w = testutil.Request(r, "GET", "/api/v1/inventory/materials", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list: got %d", w.Code)
	}
}

func TestInventoryHandler_ConsumeReceive(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)
	testutil.Request(r, "POST", "/api/v1/inventory/materials", map[string]interface{}{
		"material_id": "MAT-CR", "material_name": "Steel", "current_stock": 200,
		"min_stock": 20, "unit": "kg",
	})

	// Receive
	w := testutil.Request(r, "POST", "/api/v1/inventory/receive", map[string]interface{}{
		"material_id": "MAT-CR", "quantity": 50,
	})
	if w.Code != http.StatusOK {
		t.Fatalf("receive: got %d", w.Code)
	}

	// Consume
	w = testutil.Request(r, "POST", "/api/v1/inventory/consume", map[string]interface{}{
		"material_id": "MAT-CR", "quantity": 30, "reference_job_id": "JOB-1",
	})
	if w.Code != http.StatusOK {
		t.Fatalf("consume: got %d", w.Code)
	}
}

func TestInventoryHandler_ProductStockListOptions(t *testing.T) {
	db := testutil.NewTestDB(t)
	r := testutil.NewTestRouter(db, router.Setup)

	w := testutil.Request(r, "POST", "/api/v1/inventory/product-stock", map[string]interface{}{
		"product_id":        "P-STOCK-1",
		"quantity_on_hand":  25,
		"quantity_reserved": 5,
		"status":            "available",
		"storage_location":  "Rack A",
	})
	if w.Code != http.StatusCreated {
		t.Fatalf("create product stock: got %d, body: %s", w.Code, w.Body.String())
	}

	w = testutil.Request(r, "GET", "/api/v1/inventory/product-stock?product_id=P-STOCK-1&status=available&sort_by=product_id&sort_dir=asc&limit=10&offset=0&fields=inventory_id,product_id,status", nil)
	if w.Code != http.StatusOK {
		t.Fatalf("list product stock with query options: got %d, body: %s", w.Code, w.Body.String())
	}
}
