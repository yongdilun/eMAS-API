# API Change Runbook

Use this every time you add/change an API endpoint or Swagger comments.

## 1) Format changed Go files
```powershell
gofmt -w .\emas\internal\handler\*.go .\emas\internal\service\*.go .\emas\internal\repository\*.go .\emas\internal\handler\dto\*.go .\emas\internal\router\*.go
```

## 2) Regenerate Swagger docs
From `emas/`:
```powershell
cd .\emas
swag init -g cmd/emas/main.go -o docs
cd ..
```

## 3) Regenerate factory-agent tools from Swagger
From repo root:
```powershell
.\.venv\Scripts\python factory-agent\scripts\generate_tools.py --local
```

## 4) Run focused tests
Backend handler smoke tests:
```powershell
$env:GOCACHE='.\.gocache_test'; go test ./emas/internal/handler -count=1
```

Factory-agent core tests (quick set):
```powershell
.\.venv\Scripts\python -m pytest factory-agent/tests/test_api_endpoints.py -q
```

## 5) Verify generated files changed as expected
```powershell
git status --short
```
You should usually see updates in:
- `emas/docs/swagger.yaml`
- `emas/docs/swagger.json`
- `emas/docs/docs.go`
- `factory-agent/tools.md`

## 6) (Optional) Start services and quick health check
```powershell
# Go API
cd .\emas; go run .\cmd\emas\main.go
# in another terminal
curl http://localhost:8080/health
```

## Notes
- If you changed only business logic (no route/comment/schema change), steps 2 and 3 are optional.
- If tool behavior in chat changed, always run step 3 so planner/executor sees latest tool schemas.
