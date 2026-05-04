// Seed command populates MySQL with canonical demo/test data.
package main

import (
	"emas/config"
	"emas/internal/repository"
	"emas/internal/seeddata"
	"log"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatal("config:", err)
	}
	db, err := repository.InitDB(cfg)
	if err != nil {
		log.Fatal("db:", err)
	}
	if err := seeddata.SeedCanonical(db, seeddata.SeedOptions{Migrate: true, ValidateFingerprint: true}); err != nil {
		log.Fatal("seed:", err)
	}
}
