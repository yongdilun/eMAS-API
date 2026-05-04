package main

import (
	"emas/internal/repository"
	"emas/internal/router"
	"emas/internal/seeddata"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"github.com/gin-gonic/gin"
	_ "github.com/ncruces/go-sqlite3/embed"
	"github.com/ncruces/go-sqlite3/gormlite"
	"gorm.io/gorm"
)

func main() {
	addr := env("E2E_SERVER_ADDR", "127.0.0.1:18080")
	dbPath := env("E2E_SQLITE_PATH", filepath.Join(os.TempDir(), "emas-e2e-server.db"))
	if dbPath != ":memory:" {
		_ = os.Remove(dbPath)
	}

	db, err := gorm.Open(gormlite.Open(dbPath), &gorm.Config{})
	if err != nil {
		log.Fatalf("open e2e sqlite db: %v", err)
	}
	sqlDB, err := db.DB()
	if err != nil {
		log.Fatalf("open e2e sql db: %v", err)
	}
	sqlDB.SetMaxOpenConns(1)
	sqlDB.SetMaxIdleConns(1)

	if err := repository.AutoMigrate(db); err != nil {
		log.Fatalf("migrate e2e db: %v", err)
	}
	if err := seeddata.SeedCanonical(db, seeddata.SeedOptions{ValidateFingerprint: true}); err != nil {
		log.Fatalf("seed canonical e2e db: %v", err)
	}

	r := router.Setup(db)
	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "seed": "canonical"})
	})

	log.Printf("e2e seeded Go API listening on http://%s", addr)
	if err := r.Run(addr); err != nil {
		log.Fatalf("run e2e server: %v", err)
	}
}

func env(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
