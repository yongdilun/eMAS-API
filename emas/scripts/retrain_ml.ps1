param(
    [string]$ApiBaseUrl = "http://127.0.0.1:8080",
    [string]$OutputRoot = "ml_artifacts",
    [string]$DatasetPath = "ml_artifacts\training_dataset.json",
    [string]$PythonExe = "python",
    [int]$MinNewOutcomeRows = 200
)

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $DatasetPath) | Out-Null

$currentMetadataPath = Join-Path $OutputRoot "current\metadata.json"
$currentMetadata = $null
if (Test-Path $currentMetadataPath) {
    $currentMetadata = Get-Content $currentMetadataPath -Raw | ConvertFrom-Json
}

$statsUrl = "$($ApiBaseUrl.TrimEnd('/'))/api/v1/scheduling/training-dataset/stats"
if ($currentMetadata -and $currentMetadata.trained_at) {
    $encodedSince = [System.Uri]::EscapeDataString([string]$currentMetadata.trained_at)
    $statsUrl = "$statsUrl?since=$encodedSince"
}

$statsResponse = Invoke-RestMethod -Uri $statsUrl -Method Get
if (-not $statsResponse.success) {
    throw "training dataset stats request failed"
}
$stats = $statsResponse.data
$newOutcomeRows = 0
if ($stats.PSObject.Properties.Name -contains "outcome_rows_since") {
    $newOutcomeRows = [int]$stats.outcome_rows_since
}
if ($newOutcomeRows -lt $MinNewOutcomeRows) {
    @{
        action = "skipped"
        reason = "insufficient_new_outcomes"
        min_new_outcome_rows = $MinNewOutcomeRows
        outcome_rows_since = $newOutcomeRows
        total_rows = [int]$stats.total_rows
        latest_outcome_recorded_at = $stats.latest_outcome_recorded_at
        baseline_model_version = if ($currentMetadata) { $currentMetadata.model_version } else { $null }
    } | ConvertTo-Json -Depth 6
    exit 0
}

$datasetUrl = "$($ApiBaseUrl.TrimEnd('/'))/api/v1/scheduling/training-dataset"
Invoke-WebRequest -Uri $datasetUrl -OutFile $DatasetPath | Out-Null

$trainOutput = & $PythonExe "train_xgboost.py" --input $DatasetPath --out $OutputRoot --promote
$trainSummary = ($trainOutput | Out-String).Trim()
$parsedSummary = $null
if ($trainSummary) {
    $parsedSummary = $trainSummary | ConvertFrom-Json
}

@{
    action = if ($parsedSummary.promoted) { "trained_and_promoted" } else { "trained_candidate_only" }
    dataset_path = $DatasetPath
    outcome_rows_since = $newOutcomeRows
    total_rows = [int]$stats.total_rows
    baseline_model_version = if ($currentMetadata) { $currentMetadata.model_version } else { $null }
    trainer_summary = $parsedSummary
} | ConvertTo-Json -Depth 8
