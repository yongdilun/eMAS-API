package repository

import (
	"strings"

	"gorm.io/gorm"
)

// BaseFilter contains common fields for listing endpoints
type BaseFilter struct {
	SortBy  string
	SortDir string
	Limit   int
	Offset  int
	Fields  string
}

// ApplyPagination applies limit and offset to the query
func (f *BaseFilter) ApplyPagination(db *gorm.DB) *gorm.DB {
	if f.Limit > 0 {
		db = db.Limit(f.Limit)
	}
	if f.Offset > 0 {
		db = db.Offset(f.Offset)
	}
	return db
}

// ApplySorting applies order by to the query based on an allowlist
func (f *BaseFilter) ApplySorting(db *gorm.DB, defaultSort string, allowedFields map[string]string) *gorm.DB {
	sortBy := strings.ToLower(f.SortBy)
	dbField, ok := allowedFields[sortBy]
	if !ok {
		// Support defaults that already include direction or multiple fields.
		if strings.Contains(defaultSort, " ") || strings.Contains(defaultSort, ",") {
			return db.Order(defaultSort)
		}
		dbField = defaultSort
	}

	sortDir := strings.ToUpper(f.SortDir)
	if sortDir != "DESC" {
		sortDir = "ASC"
	}

	return db.Order(dbField + " " + sortDir)
}

// ApplyFields applies select to the query based on an allowlist
func (f *BaseFilter) ApplyFields(db *gorm.DB, allowedFields map[string]bool) *gorm.DB {
	if f.Fields == "" {
		return db
	}

	parts := strings.Split(f.Fields, ",")
	var selected []string
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if allowedFields[p] {
			selected = append(selected, p)
		}
	}

	if len(selected) > 0 {
		return db.Select(selected)
	}
	return db
}
