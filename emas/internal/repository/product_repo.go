package repository

import (
	"emas/internal/domain"
	"strings"

	"gorm.io/gorm"
)

type ProductRepository struct {
	db *gorm.DB
}

func NewProductRepository(db *gorm.DB) *ProductRepository {
	return &ProductRepository{db: db}
}

func (r *ProductRepository) Create(p *domain.Product) error {
	return r.db.Create(p).Error
}

func (r *ProductRepository) GetByID(id string) (*domain.Product, error) {
	var p domain.Product
	err := r.db.Where("product_id = ?", id).First(&p).Error
	if err != nil {
		return nil, err
	}
	return &p, nil
}

func (r *ProductRepository) GetByFormulaID(formulaID string) (*domain.Product, error) {
	var p domain.Product
	err := r.db.Where("formula_id = ?", formulaID).First(&p).Error
	if err != nil {
		return nil, err
	}
	return &p, nil
}

func (r *ProductRepository) ListAll() ([]domain.Product, error) {
	var products []domain.Product
	err := r.db.Find(&products).Error
	return products, err
}

type ProductListFilter struct {
	Status      string
	ProductType string
	SortBy      string // product_id, product_name, created_at
	SortDir     string // asc, desc
	Limit       int
	Offset      int
}

func (r *ProductRepository) ListFiltered(f ProductListFilter) ([]domain.Product, error) {
	q := r.db.Model(&domain.Product{})
	if f.Status != "" {
		q = q.Where("status = ?", f.Status)
	}
	if f.ProductType != "" {
		q = q.Where("product_type = ?", f.ProductType)
	}

	sortDir := strings.ToLower(f.SortDir)
	if sortDir != "asc" && sortDir != "desc" {
		sortDir = "asc"
	}
	sortBy := strings.ToLower(f.SortBy)
	switch sortBy {
	case "product_name":
		q = q.Order("product_name " + sortDir)
	case "created_at":
		q = q.Order("created_at " + sortDir)
	default:
		q = q.Order("product_id " + sortDir)
	}
	if f.Limit > 0 {
		q = q.Limit(f.Limit)
	}
	if f.Offset > 0 {
		q = q.Offset(f.Offset)
	}

	var products []domain.Product
	if err := q.Find(&products).Error; err != nil {
		return nil, err
	}
	return products, nil
}

func (r *ProductRepository) Update(p *domain.Product) error {
	return r.db.Save(p).Error
}

func (r *ProductRepository) Delete(id string) error {
	return r.db.Where("product_id = ?", id).Delete(&domain.Product{}).Error
}
