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
This updates both:
- the DB-backed tool registry used by the agent at runtime
- `factory-agent/tools.md`

Important:
- `factory-agent/tools.md` alone is not the source of truth at runtime.
- The planner/executor loads tools from the database-backed registry first.
- A correct-looking `tools.md` does not guarantee the live registry schema is correct.

## 4) Run focused tests
Backend handler smoke tests:
```powershell
$env:GOCACHE='.\.gocache_test'; go test ./emas/internal/handler -count=1
```

Factory-agent core tests (quick set):
```powershell
.\.venv\Scripts\python -m pytest factory-agent/tests/test_api_endpoints.py -q
```

Factory-agent planner contract tests:
```powershell
.\.venv\Scripts\python -m pytest factory-agent/tests/test_planner.py -q
```

If you changed enum/query filters, tool schemas, or Swagger parameter annotations, also run:
```powershell
.\.venv\Scripts\python -m pytest factory-agent/tests/test_toolgen.py factory-agent/tests/test_planner.py -q
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

Then inspect the changed tool entry in `factory-agent/tools.md` and confirm:
- enum values are present when expected
- `x-query-params` includes query filters that should be planner-visible
- `x-param-sources` marks each field correctly as `query`, `path`, or `body`
- required fields still match the endpoint contract

For machine status filters, for example, `get__machines` should keep:
- `status` as a query parameter
- the status enum values such as `idle`, `running`, `maintenance`, `offline`

Suggested quick checks:
```powershell
Select-String -Path .\factory-agent\tools.md -Pattern '## get__machines','"status"','"enum"','"x-query-params"','"x-param-sources"' -Context 0,20
```

If the generated markdown looks right but chat/planning still behaves wrong, verify the live registry was regenerated from the same Swagger source. The runtime app can auto-repair the DB registry from `emas/docs/swagger.json`, so stale local Swagger can repopulate bad schemas later.

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
- If planner behavior changed for phrases like `find all running machine`, treat that as a schema regression first, not just a prompt/planner issue.
- When debugging chat/tool-selection drift, compare all three layers:
  1. Go Swagger output in `emas/docs/swagger.json`
  2. generated `factory-agent/tools.md`
  3. the live DB-backed registry loaded by the agent
