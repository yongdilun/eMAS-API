import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from xgboost import Booster


def resolve_artifact_dir() -> Path:
    env_dir = os.getenv("ML_ARTIFACT_DIR")
    if env_dir:
        return Path(env_dir)
    current_dir = Path("ml_artifacts/current")
    if current_dir.exists():
        return current_dir
    return Path("ml_artifacts")


ARTIFACT_DIR = resolve_artifact_dir()
INFERENCE_METRICS = {"prediction_count": 0, "failure_count": 0, "total_latency_ms": 0.0}
ARTIFACT_STATE = {"signature": None, "loaded_model_version": "unloaded"}


class PredictRequest(BaseModel):
    job_id: str
    product_id: str
    job_priority: Optional[str] = None

    material_shortage_count: int = 0
    sub_product_shortage_count: int = 0
    can_start_now: Optional[bool] = None

    now: Optional[str] = None
    deadline: Optional[str] = None
    estimated_completion: Optional[str] = None

    snapshot_machine_ids: list[str] = Field(default_factory=list)
    queue_lengths_vector: list[int] = Field(default_factory=list)
    machine_utilization_vector: list[float] = Field(default_factory=list)

    queue_wait_minutes: int = 0
    queue_len_at_plan: int = 0
    max_queue_len: int = 0
    util_1h: float = 0.0
    util_8h: float = 0.0
    util_24h: float = 0.0
    util_7d: float = 0.0
    same_product_delay_rate_30d: float = 0.0
    same_step_delay_rate_30d: float = 0.0
    same_machine_step_delay_rate_30d: float = 0.0
    prior_delay_count_product_30d: float = 0.0
    prior_delay_count_step_30d: float = 0.0
    changeover_count_24h: int = 0
    setup_minutes_prev_changeover: int = 0
    same_product_as_prev_machine_job: bool = False
    upstream_lateness_minutes: int = 0
    readiness_delay_minutes: int = 0
    planned_duration_mins: float = 0.0
    planned_vs_actual_duration_ratio: float = 0.0
    completion_ratio: float = 0.0
    scrap_rate: float = 0.0
    hours_to_shift_end: float = 0.0
    day_of_week: int = 0
    is_holiday: bool = False
    is_near_holiday: bool = False
    is_weekend: bool = False
    allocation_percent: float = 0.0
    quantity_planned: float = 0.0
    produced_qty: float = 0.0
    scrap_qty: float = 0.0
    machine_utilization_rate: float = 0.0
    machine_efficiency_factor: float = 1.0
    maintenance_due_in_days: float = 0.0
    allow_parallel_execution: bool = False
    max_parallel_machines: float = 0.0
    min_split_qty: float = 0.0
    transfer_batch_size: float = 0.0
    shift_name: str = ""
    prev_product_id_on_machine: str = ""


class PredictResponse(BaseModel):
    probability_of_delay: float
    delay_severity: str
    predicted_delay_minutes: int
    confidence_score: float
    feature_summary: list[str]
    fallback_recommended: bool
    model_version: str
    latency_ms: float


@dataclass
class FeatureSchema:
    feature_cols: list[str]
    priority_levels: list[str]
    shift_levels: list[str]
    version: str


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"missing {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_schema() -> FeatureSchema:
    data = _read_json(ARTIFACT_DIR / "feature_schema.json")
    return FeatureSchema(
        feature_cols=data["feature_cols"],
        priority_levels=data.get("priority_levels", ["low", "medium", "high", "urgent"]),
        shift_levels=data.get("shift_levels", ["", "A", "B", "C", "Night"]),
        version=data.get("version", "xgb-unknown"),
    )


def _load_booster(path: Path) -> Booster:
    if not path.exists():
        raise FileNotFoundError(f"missing {path}")
    booster = Booster()
    booster.load_model(str(path))
    return booster


def _artifact_signature() -> tuple[tuple[str, int], ...]:
    tracked = [
        "feature_schema.json",
        "metadata.json",
        "evaluation.json",
        "model_delay.json",
        "model_delay_minutes.json",
    ]
    signature = []
    for name in tracked:
        path = ARTIFACT_DIR / name
        stat = path.stat() if path.exists() else None
        signature.append((name, stat.st_mtime_ns if stat else -1))
    return tuple(signature)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    candidate = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _severity_from_minutes(minutes: float) -> str:
    if minutes <= 0:
        return "Low"
    if minutes <= 60:
        return "Medium"
    return "High"


def _priority_one_hot(priority: str, levels: list[str]) -> dict[str, int]:
    normalized = (priority or "").strip().lower()
    return {f"priority_{level}": int(normalized == level) for level in levels}


def _shift_one_hot(shift_name: str, levels: list[str]) -> dict[str, int]:
    normalized = shift_name or ""
    out = {}
    for level in levels:
        suffix = "unknown" if level == "" else level.lower()
        out[f"shift_{suffix}"] = int(normalized == level)
    return out


def _vector_aggregates(req: PredictRequest) -> tuple[int, float]:
    max_queue = int(max(req.queue_lengths_vector)) if req.queue_lengths_vector else 0
    mean_util = float(np.mean(req.machine_utilization_vector)) if req.machine_utilization_vector else 0.0
    if not np.isfinite(mean_util):
        mean_util = 0.0
    return max_queue, max(0.0, mean_util)


def build_feature_row(req: PredictRequest, schema: FeatureSchema) -> tuple[dict[str, float], float]:
    max_queue_from_vectors, mean_util_from_vectors = _vector_aggregates(req)
    now_dt = _parse_dt(req.now) or datetime.now(timezone.utc)
    deadline_dt = _parse_dt(req.deadline)
    est_completion_dt = _parse_dt(req.estimated_completion)

    minutes_to_deadline = 0.0
    minutes_after_deadline_at_plan = 0.0
    if deadline_dt:
        minutes_to_deadline = (deadline_dt - now_dt).total_seconds() / 60.0
        if est_completion_dt:
            minutes_after_deadline_at_plan = max(
                0.0, (est_completion_dt - deadline_dt).total_seconds() / 60.0
            )

    base = {
        "material_shortage_count": float(req.material_shortage_count),
        "sub_product_shortage_count": float(req.sub_product_shortage_count),
        "queue_wait_minutes": float(req.queue_wait_minutes),
        "queue_len_at_plan": float(req.queue_len_at_plan or max_queue_from_vectors),
        "max_queue_len": float(req.max_queue_len or max_queue_from_vectors),
        "util_1h": float(req.util_1h or mean_util_from_vectors),
        "util_8h": float(req.util_8h or mean_util_from_vectors),
        "util_24h": float(req.util_24h or mean_util_from_vectors),
        "util_7d": float(req.util_7d or mean_util_from_vectors),
        "same_product_delay_rate_30d": float(req.same_product_delay_rate_30d),
        "same_step_delay_rate_30d": float(req.same_step_delay_rate_30d),
        "same_machine_step_delay_rate_30d": float(req.same_machine_step_delay_rate_30d),
        "prior_delay_count_product_30d": float(req.prior_delay_count_product_30d),
        "prior_delay_count_step_30d": float(req.prior_delay_count_step_30d),
        "changeover_count_24h": float(req.changeover_count_24h),
        "setup_minutes_prev_changeover": float(req.setup_minutes_prev_changeover),
        "same_product_as_prev_machine_job": float(req.same_product_as_prev_machine_job),
        "upstream_lateness_minutes": float(req.upstream_lateness_minutes),
        "readiness_delay_minutes": float(req.readiness_delay_minutes),
        "minutes_to_deadline": float(minutes_to_deadline),
        "minutes_after_deadline_at_plan": float(minutes_after_deadline_at_plan),
        "planned_duration_mins": float(req.planned_duration_mins),
        "planned_vs_actual_duration_ratio": float(req.planned_vs_actual_duration_ratio),
        "completion_ratio": float(req.completion_ratio),
        "scrap_rate": float(req.scrap_rate),
        "hours_to_shift_end": float(req.hours_to_shift_end),
        "day_of_week": float(req.day_of_week),
        "is_holiday": float(req.is_holiday),
        "is_near_holiday": float(req.is_near_holiday),
        "is_weekend": float(req.is_weekend),
        "can_start_now_int": float(bool(req.can_start_now)),
        "allocation_percent": float(req.allocation_percent),
        "quantity_planned": float(req.quantity_planned),
        "produced_qty": float(req.produced_qty),
        "scrap_qty": float(req.scrap_qty),
        "machine_utilization_rate": float(req.machine_utilization_rate or mean_util_from_vectors),
        "machine_efficiency_factor": float(req.machine_efficiency_factor or 1.0),
        "maintenance_due_in_days": float(req.maintenance_due_in_days),
        "allow_parallel_execution": float(req.allow_parallel_execution),
        "max_parallel_machines": float(req.max_parallel_machines),
        "min_split_qty": float(req.min_split_qty),
        "transfer_batch_size": float(req.transfer_batch_size),
        "prev_product_nonempty": float(bool(req.prev_product_id_on_machine)),
    }
    base.update(_priority_one_hot(req.job_priority or "", schema.priority_levels))
    base.update(_shift_one_hot(req.shift_name, schema.shift_levels))

    coverage_fields = {
        "job_priority": bool(req.job_priority),
        "material_shortage_count": req.material_shortage_count != 0,
        "sub_product_shortage_count": req.sub_product_shortage_count != 0,
        "can_start_now": req.can_start_now is not None,
        "deadline": deadline_dt is not None,
        "estimated_completion": est_completion_dt is not None,
        "queue_lengths_vector": bool(req.queue_lengths_vector),
        "machine_utilization_vector": bool(req.machine_utilization_vector),
        "queue_wait_minutes": req.queue_wait_minutes != 0,
        "upstream_lateness_minutes": req.upstream_lateness_minutes != 0,
        "util_24h": req.util_24h != 0.0 or bool(req.machine_utilization_vector),
    }
    feature_coverage = sum(int(v) for v in coverage_fields.values()) / float(len(coverage_fields))

    for col in schema.feature_cols:
        base.setdefault(col, 0.0)
    return ({col: float(base[col]) for col in schema.feature_cols}, feature_coverage)


def build_feature_summary(req: PredictRequest, row: dict[str, float]) -> list[str]:
    reasons: list[str] = []
    if req.material_shortage_count > 0 or req.sub_product_shortage_count > 0:
        reasons.append("material or sub-product shortages detected")
    if row.get("max_queue_len", 0.0) >= 3 or row.get("queue_wait_minutes", 0.0) >= 60:
        reasons.append("high recent queue congestion")
    if row.get("upstream_lateness_minutes", 0.0) > 0:
        reasons.append("upstream step already late")
    if max(row.get("util_8h", 0.0), row.get("util_24h", 0.0)) >= 0.85:
        reasons.append("machine utilization is elevated")
    if row.get("minutes_after_deadline_at_plan", 0.0) > 0 or row.get("minutes_to_deadline", 0.0) <= 120:
        reasons.append("deadline slack is tight")
    if row.get("changeover_count_24h", 0.0) > 0 and not req.same_product_as_prev_machine_job:
        reasons.append("recent changeover pressure is elevated")
    if not reasons:
        reasons.append("prediction is based on stable observed scheduling inputs")
    return reasons[:3]


app = FastAPI(title="eMas ML Risk API", version="2.0")


def _load_artifacts(force: bool = False) -> None:
    global _schema, _delay_booster, _mins_booster, _metadata, _evaluation
    signature = _artifact_signature()
    if not force and ARTIFACT_STATE["signature"] == signature:
        return
    _schema = _load_schema()
    _delay_booster = _load_booster(ARTIFACT_DIR / "model_delay.json")
    _mins_booster = _load_booster(ARTIFACT_DIR / "model_delay_minutes.json")
    _metadata = _read_optional_json(ARTIFACT_DIR / "metadata.json")
    _evaluation = _read_optional_json(ARTIFACT_DIR / "evaluation.json")
    ARTIFACT_STATE["signature"] = signature
    ARTIFACT_STATE["loaded_model_version"] = _metadata.get("model_version", _schema.version)


def ensure_artifacts_loaded() -> None:
    _load_artifacts(force=False)


@app.on_event("startup")
def _startup() -> None:
    _load_artifacts(force=True)


@app.get("/health")
def health() -> dict[str, Any]:
    ensure_artifacts_loaded()
    avg_latency = (
        INFERENCE_METRICS["total_latency_ms"] / INFERENCE_METRICS["prediction_count"]
        if INFERENCE_METRICS["prediction_count"]
        else 0.0
    )
    classifier_eval = (_evaluation.get("classifier") or {}).get("validation") or {}
    return {
        "ok": True,
        "model_version": _metadata.get("model_version", getattr(_schema, "version", "unknown")),
        "trained_at": _metadata.get("trained_at"),
        "artifact_dir": str(ARTIFACT_DIR),
        "data_window_start": _metadata.get("data_window_start"),
        "data_window_end": _metadata.get("data_window_end"),
        "feature_schema_version": _metadata.get("feature_schema_version", getattr(_schema, "version", "unknown")),
        "evaluation_summary": {
            "validation_auc": classifier_eval.get("auc"),
            "validation_recall": classifier_eval.get("recall"),
            "feature_coverage_rate": ((_evaluation.get("operational") or {}).get("feature_coverage_rate")),
        },
        "inference_metrics": {
            "prediction_count": INFERENCE_METRICS["prediction_count"],
            "failure_count": INFERENCE_METRICS["failure_count"],
            "mean_latency_ms": avg_latency,
            "currently_loaded_model_version": ARTIFACT_STATE["loaded_model_version"],
        },
    }


@app.post("/predict-delay-risk", response_model=PredictResponse)
def predict(req: PredictRequest) -> PredictResponse:
    t0 = time.perf_counter()
    try:
        ensure_artifacts_loaded()
        row, feature_coverage = build_feature_row(req, _schema)
        x = np.array([[row[col] for col in _schema.feature_cols]], dtype=np.float32)
        probability = float(_delay_booster.inplace_predict(x)[0])
        probability = min(1.0, max(0.0, probability))
        predicted_minutes = float(_mins_booster.inplace_predict(x)[0])
        if not np.isfinite(predicted_minutes):
            predicted_minutes = 0.0
        predicted_minutes = max(0.0, predicted_minutes)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        INFERENCE_METRICS["prediction_count"] += 1
        INFERENCE_METRICS["total_latency_ms"] += latency_ms

        confidence = min(1.0, 0.65 * max(probability, 1.0 - probability) + 0.35 * feature_coverage)
        feature_summary = build_feature_summary(req, row)
        fallback_recommended = confidence < 0.60

        return PredictResponse(
            probability_of_delay=probability,
            delay_severity=_severity_from_minutes(predicted_minutes),
            predicted_delay_minutes=int(round(predicted_minutes)),
            confidence_score=confidence,
            feature_summary=feature_summary,
            fallback_recommended=fallback_recommended,
            model_version=_metadata.get("model_version", _schema.version),
            latency_ms=latency_ms,
        )
    except FileNotFoundError as exc:
        INFERENCE_METRICS["failure_count"] += 1
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        INFERENCE_METRICS["failure_count"] += 1
        raise HTTPException(status_code=500, detail=f"prediction_failed: {exc}")
