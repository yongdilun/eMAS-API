import argparse
import json
import shutil
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    roc_auc_score,
)
from xgboost import XGBClassifier, XGBRegressor


PRIORITY_LEVELS = ["low", "medium", "high", "urgent"]
SHIFT_LEVELS = ["", "A", "B", "C", "Night"]
FEATURE_SCHEMA_VERSION = "xgb-v2"
DEFAULT_COVERAGE_THRESHOLD = 0.85


def load_dataset(path: Path) -> list[dict]:
    if path.suffix.lower() == ".jsonl":
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("rows", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise SystemExit(f"unsupported dataset shape in {path}")


def _series(df: pd.DataFrame, name: str, default=None) -> pd.Series:
    if name in df.columns:
        return df[name]
    return pd.Series([default] * len(df), index=df.index)


def _bool_as_int(series: pd.Series) -> pd.Series:
    return series.map(lambda value: bool(value) if pd.notna(value) else False).astype(int)


def _numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(default)


def _parse_datetimes(df: pd.DataFrame) -> None:
    for col in [
        "scheduled_start",
        "scheduled_end",
        "actual_start",
        "actual_end",
        "job_deadline",
        "earliest_ready_at",
        "captured_at",
        "outcome_recorded_at",
    ]:
        df[f"{col}_dt"] = pd.to_datetime(_series(df, col), utc=True, errors="coerce")


def _compute_history_features(
    df: pd.DataFrame,
    ts_col: str,
    group_cols: list[str],
    delayed_col: str,
    count_col: str,
    rate_col: str,
) -> None:
    counts = pd.Series(0.0, index=df.index)
    rates = pd.Series(0.0, index=df.index)
    window = pd.Timedelta(days=30)
    sort_cols = list(group_cols) + [ts_col]
    grouped = df.sort_values(sort_cols).groupby(group_cols, dropna=False, sort=False)
    for _, group in grouped:
        history = deque()
        delayed_sum = 0
        for idx, row in group.iterrows():
            ts = row[ts_col]
            if pd.isna(ts):
                counts.loc[idx] = 0.0
                rates.loc[idx] = 0.0
            else:
                while history and history[0][0] < ts - window:
                    _, delayed = history.popleft()
                    delayed_sum -= delayed
                counts.loc[idx] = float(len(history))
                rates.loc[idx] = float(delayed_sum / len(history)) if history else 0.0
                delayed = int(row[delayed_col])
                history.append((ts, delayed))
                delayed_sum += delayed
    df[count_col] = counts
    df[rate_col] = rates


def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    _parse_datetimes(df)
    df["product_id"] = _series(df, "product_id", "").fillna("").astype(str)
    df["step_id"] = _series(df, "step_id", "").fillna("").astype(str)
    df["machine_id"] = _series(df, "machine_id", "").fillna("").astype(str)

    df["delay_minutes"] = _numeric(_series(df, "delay_minutes"), 0).astype(int)
    df["is_delayed"] = (df["delay_minutes"] > 0).astype(int)
    if df["is_delayed"].nunique() < 2:
        median_delay = float(df["delay_minutes"].quantile(0.5))
        df["is_delayed"] = (df["delay_minutes"] > median_delay).astype(int)

    df["planned_duration_mins"] = _numeric(_series(df, "planned_duration_mins"))
    if "planned_duration_mins" not in df.columns or (df["planned_duration_mins"] == 0).all():
        df["planned_duration_mins"] = (
            (df["scheduled_end_dt"] - df["scheduled_start_dt"]).dt.total_seconds() / 60.0
        ).fillna(0.0)
    df["actual_duration_mins"] = _numeric(_series(df, "actual_duration_mins"))
    df["planned_vs_actual_duration_ratio"] = _numeric(_series(df, "planned_vs_actual_ratio"))
    missing_ratio = df["planned_vs_actual_duration_ratio"] <= 0
    valid_ratio = df["planned_duration_mins"] > 0
    df.loc[missing_ratio & valid_ratio, "planned_vs_actual_duration_ratio"] = (
        df.loc[missing_ratio & valid_ratio, "actual_duration_mins"]
        / df.loc[missing_ratio & valid_ratio, "planned_duration_mins"]
    )

    df["queue_wait_minutes"] = _numeric(_series(df, "queue_wait_minutes"))
    df["queue_len_at_plan"] = _numeric(_series(df, "queue_len_at_plan"))
    df["max_queue_len"] = _numeric(_series(df, "max_queue_len"))
    df["util_1h"] = _numeric(_series(df, "util_1h"))
    df["util_8h"] = _numeric(_series(df, "util_8h"))
    df["util_24h"] = _numeric(_series(df, "util_24h"))
    df["util_7d"] = _numeric(_series(df, "util_7d"))
    df["material_shortage_count"] = _numeric(_series(df, "material_shortage_count"))
    df["sub_product_shortage_count"] = _numeric(_series(df, "sub_product_shortage_count"))
    df["upstream_lateness_minutes"] = _numeric(_series(df, "upstream_lateness_minutes"))
    df["readiness_delay_minutes"] = _numeric(_series(df, "readiness_delay_minutes"))
    df["changeover_count_24h"] = _numeric(_series(df, "changeover_count_24h"))
    df["setup_minutes_prev_changeover"] = _numeric(_series(df, "setup_minutes_prev_changeover"))
    df["completion_ratio"] = _numeric(_series(df, "completion_ratio"))
    df["scrap_rate"] = _numeric(_series(df, "scrap_rate"))
    df["hours_to_shift_end"] = _numeric(_series(df, "hours_to_shift_end"))
    df["same_product_as_prev_machine_job"] = _bool_as_int(_series(df, "same_product_as_prev_machine_job"))
    df["is_holiday"] = _bool_as_int(_series(df, "is_holiday"))
    df["is_near_holiday"] = _bool_as_int(_series(df, "is_near_holiday"))
    df["is_weekend"] = _bool_as_int(_series(df, "is_weekend"))
    df["can_start_now_int"] = _bool_as_int(_series(df, "can_start_now"))
    df["day_of_week"] = _numeric(_series(df, "day_of_week"))

    df["feature_ts"] = df["scheduled_start_dt"].copy()
    missing_ts = df["feature_ts"].isna()
    df.loc[missing_ts, "feature_ts"] = df.loc[missing_ts, "captured_at_dt"]
    missing_ts = df["feature_ts"].isna()
    df.loc[missing_ts, "feature_ts"] = df.loc[missing_ts, "scheduled_end_dt"]
    if df["feature_ts"].isna().all():
        raise SystemExit("dataset missing usable timestamps for time-based split")

    df["minutes_to_deadline"] = 0.0
    deadline_mask = df["job_deadline_dt"].notna() & df["scheduled_start_dt"].notna()
    df.loc[deadline_mask, "minutes_to_deadline"] = (
        (df.loc[deadline_mask, "job_deadline_dt"] - df.loc[deadline_mask, "scheduled_start_dt"])
        .dt.total_seconds()
        / 60.0
    )
    df["minutes_after_deadline_at_plan"] = 0.0
    late_mask = df["job_deadline_dt"].notna() & df["scheduled_end_dt"].notna()
    df.loc[late_mask, "minutes_after_deadline_at_plan"] = np.maximum(
        0.0,
        (
            (df.loc[late_mask, "scheduled_end_dt"] - df.loc[late_mask, "job_deadline_dt"])
            .dt.total_seconds()
            / 60.0
        ),
    )

    df["machine_step_key"] = (
        _series(df, "machine_id", "").fillna("").astype(str)
        + "::"
        + _series(df, "step_id", "").fillna("").astype(str)
    )
    _compute_history_features(
        df,
        "feature_ts",
        ["product_id"],
        "is_delayed",
        "prior_delay_count_product_30d",
        "same_product_delay_rate_30d",
    )
    _compute_history_features(
        df,
        "feature_ts",
        ["step_id"],
        "is_delayed",
        "prior_delay_count_step_30d",
        "same_step_delay_rate_30d",
    )
    _compute_history_features(
        df,
        "feature_ts",
        ["machine_step_key"],
        "is_delayed",
        "prior_delay_count_machine_step_30d",
        "same_machine_step_delay_rate_30d",
    )

    priority = _series(df, "job_priority", "").fillna("").astype(str).str.lower()
    shift_name = _series(df, "shift_name", "").fillna("").astype(str)
    prev_product = _series(df, "prev_product_id_on_machine", "").fillna("").astype(str)
    prev_product_nonempty = (prev_product != "").astype(int)
    for level in PRIORITY_LEVELS:
        df[f"priority_{level}"] = (priority == level).astype(int)
    for level in SHIFT_LEVELS:
        suffix = "unknown" if level == "" else level.lower()
        df[f"shift_{suffix}"] = (shift_name == level).astype(int)

    feature_cols = [
        "material_shortage_count",
        "sub_product_shortage_count",
        "queue_wait_minutes",
        "queue_len_at_plan",
        "max_queue_len",
        "util_1h",
        "util_8h",
        "util_24h",
        "util_7d",
        "same_product_delay_rate_30d",
        "same_step_delay_rate_30d",
        "same_machine_step_delay_rate_30d",
        "prior_delay_count_product_30d",
        "prior_delay_count_step_30d",
        "changeover_count_24h",
        "setup_minutes_prev_changeover",
        "same_product_as_prev_machine_job",
        "upstream_lateness_minutes",
        "readiness_delay_minutes",
        "minutes_to_deadline",
        "minutes_after_deadline_at_plan",
        "planned_duration_mins",
        "planned_vs_actual_duration_ratio",
        "completion_ratio",
        "scrap_rate",
        "hours_to_shift_end",
        "day_of_week",
        "is_holiday",
        "is_near_holiday",
        "is_weekend",
        "can_start_now_int",
        "allocation_percent",
        "quantity_planned",
        "produced_qty",
        "scrap_qty",
        "machine_utilization_rate",
        "machine_efficiency_factor",
        "maintenance_due_in_days",
        "allow_parallel_execution",
        "max_parallel_machines",
        "min_split_qty",
        "transfer_batch_size",
        "prev_product_nonempty",
        *[f"priority_{level}" for level in PRIORITY_LEVELS],
        *[f"shift_{'unknown' if level == '' else level.lower()}" for level in SHIFT_LEVELS],
    ]

    df["allocation_percent"] = _numeric(_series(df, "allocation_percent"))
    df["quantity_planned"] = _numeric(_series(df, "quantity_planned"))
    df["produced_qty"] = _numeric(_series(df, "produced_qty"))
    df["scrap_qty"] = _numeric(_series(df, "scrap_qty"))
    df["machine_utilization_rate"] = _numeric(_series(df, "machine_utilization_rate"))
    df["machine_efficiency_factor"] = _numeric(_series(df, "machine_efficiency_factor"), 1.0)
    df["maintenance_due_in_days"] = _numeric(_series(df, "maintenance_due_in_days"))
    df["allow_parallel_execution"] = _bool_as_int(_series(df, "allow_parallel_execution"))
    df["max_parallel_machines"] = _numeric(_series(df, "max_parallel_machines"))
    df["min_split_qty"] = _numeric(_series(df, "min_split_qty"))
    df["transfer_batch_size"] = _numeric(_series(df, "transfer_batch_size"))
    df["prev_product_nonempty"] = prev_product_nonempty

    raw_features = df[feature_cols].copy()
    X = raw_features.fillna(0.0).astype(float)
    schema = {
        "feature_cols": feature_cols,
        "priority_levels": PRIORITY_LEVELS,
        "shift_levels": SHIFT_LEVELS,
        "version": FEATURE_SCHEMA_VERSION,
    }
    return X, schema, raw_features


def time_based_split(df: pd.DataFrame) -> tuple[pd.Index, pd.Index, pd.Index]:
    order = df.sort_values("feature_ts").index.to_list()
    n = len(order)
    if n < 3:
        raise SystemExit("need at least 3 rows for time-based split")
    train_end = max(1, int(n * 0.70))
    val_end = max(train_end + 1, int(n * 0.85))
    if val_end >= n:
        val_end = n - 1
    if train_end >= val_end:
        train_end = max(1, val_end - 1)
    return (
        pd.Index(order[:train_end]),
        pd.Index(order[train_end:val_end]),
        pd.Index(order[val_end:]),
    )


def classifier_metrics(y_true: pd.Series, prob: np.ndarray) -> dict:
    pred = (prob >= 0.5).astype(int)
    out = {
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
    }
    if pd.Series(y_true).nunique() >= 2:
        out["auc"] = float(roc_auc_score(y_true, prob))
    else:
        out["auc"] = None
    return out


def regressor_metrics(y_true: pd.Series, pred: np.ndarray) -> dict:
    return {
        "mae": float(mean_absolute_error(y_true, pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, pred))),
    }


def feature_coverage_rate(raw_features: pd.DataFrame, idx: pd.Index) -> float:
    if len(raw_features) == 0 or len(idx) == 0:
        return 0.0
    return float(raw_features.loc[idx].notna().mean().mean())


def calibration_summary(y_true: pd.Series, prob: np.ndarray) -> dict:
    bins = [0.0, 0.2, 0.4, 0.6, 0.8, 1.000001]
    rows = []
    weighted_accuracy = 0.0
    total = len(prob)
    if total == 0:
        return {"bucket_accuracy": 0.0, "buckets": rows}
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(prob, dtype=float)
    for lower, upper in zip(bins[:-1], bins[1:]):
        mask = (p >= lower) & (p < upper)
        count = int(mask.sum())
        if count == 0:
            continue
        mean_prob = float(p[mask].mean())
        observed_rate = float(y[mask].mean())
        bucket_accuracy = max(0.0, 1.0 - abs(mean_prob - observed_rate))
        weighted_accuracy += bucket_accuracy * count
        rows.append(
            {
                "lower": lower,
                "upper": min(1.0, upper),
                "count": count,
                "mean_probability": mean_prob,
                "observed_rate": observed_rate,
                "bucket_accuracy": bucket_accuracy,
            }
        )
    return {
        "bucket_accuracy": float(weighted_accuracy / total),
        "buckets": rows,
    }


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_artifacts(
    candidate_dir: Path,
    clf: XGBClassifier,
    reg: XGBRegressor,
    schema: dict,
    metadata: dict,
    evaluation: dict,
) -> None:
    candidate_dir.mkdir(parents=True, exist_ok=True)
    clf.get_booster().save_model(str(candidate_dir / "model_delay.json"))
    reg.get_booster().save_model(str(candidate_dir / "model_delay_minutes.json"))
    (candidate_dir / "feature_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    (candidate_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (candidate_dir / "evaluation.json").write_text(json.dumps(evaluation, indent=2), encoding="utf-8")


def promote_candidate(candidate_dir: Path, current_dir: Path) -> None:
    if current_dir.exists():
        shutil.rmtree(current_dir)
    shutil.copytree(candidate_dir, current_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="simulator_output/simulated_training.jsonl")
    parser.add_argument("--out", default="ml_artifacts")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--promote", dest="promote", action="store_true")
    parser.add_argument("--no-promote", dest="promote", action="store_false")
    parser.set_defaults(promote=True)
    parser.add_argument("--min-feature-coverage", type=float, default=DEFAULT_COVERAGE_THRESHOLD)
    args = parser.parse_args()

    np.random.seed(args.seed)
    input_path = Path(args.input)
    out_root = Path(args.out)
    current_dir = out_root / "current"
    archive_root = out_root / "archive"
    out_root.mkdir(parents=True, exist_ok=True)
    archive_root.mkdir(parents=True, exist_ok=True)

    rows = load_dataset(input_path)
    if not rows:
        raise SystemExit(f"no rows found in {input_path}")

    df = pd.DataFrame(rows)
    X, schema, raw_features = build_features(df)
    train_idx, val_idx, test_idx = time_based_split(df)
    feature_coverage = feature_coverage_rate(raw_features, df.index)
    validation_feature_coverage = feature_coverage_rate(raw_features, val_idx)
    test_feature_coverage = feature_coverage_rate(raw_features, test_idx)

    y_clf = df["is_delayed"].astype(int)
    y_reg = _numeric(df["delay_minutes"])

    clf = XGBClassifier(
        n_estimators=350,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="binary:logistic",
        n_jobs=0,
        random_state=args.seed,
        tree_method="hist",
    )
    clf.fit(X.loc[train_idx], y_clf.loc[train_idx])
    val_prob = clf.predict_proba(X.loc[val_idx])[:, 1]
    test_prob = clf.predict_proba(X.loc[test_idx])[:, 1]

    reg = XGBRegressor(
        n_estimators=350,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="reg:squarederror",
        n_jobs=0,
        random_state=args.seed,
        tree_method="hist",
    )
    reg.fit(X.loc[train_idx], y_reg.loc[train_idx])
    val_pred_delay = reg.predict(X.loc[val_idx])
    test_pred_delay = reg.predict(X.loc[test_idx])

    trained_at = datetime.now(timezone.utc)
    model_version = f"{FEATURE_SCHEMA_VERSION}-{trained_at.strftime('%Y%m%d%H%M%S')}"
    candidate_dir = archive_root / model_version

    calibration = calibration_summary(y_clf.loc[test_idx], test_prob)
    evaluation = {
        "splits": {
            "train_rows": int(len(train_idx)),
            "validation_rows": int(len(val_idx)),
            "test_rows": int(len(test_idx)),
        },
        "classifier": {
            "validation": classifier_metrics(y_clf.loc[val_idx], val_prob),
            "test": classifier_metrics(y_clf.loc[test_idx], test_prob),
        },
        "regressor": {
            "validation": regressor_metrics(y_reg.loc[val_idx], val_pred_delay),
            "test": regressor_metrics(y_reg.loc[test_idx], test_pred_delay),
        },
        "operational": {
            "feature_coverage_rate": feature_coverage,
            "validation_feature_coverage_rate": validation_feature_coverage,
            "test_feature_coverage_rate": test_feature_coverage,
            "late_job_recall_test": classifier_metrics(y_clf.loc[test_idx], test_prob)["recall"],
            "probability_bucket_accuracy": calibration["bucket_accuracy"],
            "calibration_summary": calibration["buckets"],
        },
    }

    current_metadata = read_json(current_dir / "metadata.json")
    current_evaluation = read_json(current_dir / "evaluation.json")
    baseline_model_version = (current_metadata or {}).get("model_version")
    promotion_reasons = []
    should_promote = args.promote

    candidate_val_auc = evaluation["classifier"]["validation"]["auc"]
    candidate_val_recall = evaluation["classifier"]["validation"]["recall"]
    candidate_test_mae = evaluation["regressor"]["test"]["mae"]
    baseline_comparison = {
        "baseline_model_version": baseline_model_version,
        "validation_auc": None,
        "validation_recall": None,
        "test_mae": None,
        "feature_coverage_rate": None,
    }

    if feature_coverage < args.min_feature_coverage:
        should_promote = False
        promotion_reasons.append(
            f"feature_coverage_below_threshold ({feature_coverage:.3f} < {args.min_feature_coverage:.3f})"
        )

    if current_evaluation:
        baseline_val_auc = (((current_evaluation.get("classifier") or {}).get("validation") or {}).get("auc"))
        baseline_val_recall = (((current_evaluation.get("classifier") or {}).get("validation") or {}).get("recall"))
        baseline_test_mae = (((current_evaluation.get("regressor") or {}).get("test") or {}).get("mae"))
        baseline_feature_coverage = (((current_evaluation.get("operational") or {}).get("feature_coverage_rate")))
        baseline_comparison.update(
            {
                "validation_auc": baseline_val_auc,
                "validation_recall": baseline_val_recall,
                "test_mae": baseline_test_mae,
                "feature_coverage_rate": baseline_feature_coverage,
            }
        )
        if baseline_val_auc is not None and candidate_val_auc is not None and candidate_val_auc <= baseline_val_auc:
            should_promote = False
            promotion_reasons.append(
                f"validation_auc_not_improved ({candidate_val_auc:.4f} <= {baseline_val_auc:.4f})"
            )
        if baseline_val_recall is not None and candidate_val_recall + 0.02 < baseline_val_recall:
            should_promote = False
            promotion_reasons.append(
                f"validation_recall_regressed ({candidate_val_recall:.4f} < {baseline_val_recall:.4f} - 0.02)"
            )
        if baseline_test_mae is not None and candidate_test_mae > baseline_test_mae * 1.05:
            should_promote = False
            promotion_reasons.append(
                f"test_mae_regressed ({candidate_test_mae:.4f} > {baseline_test_mae * 1.05:.4f})"
            )
    else:
        promotion_reasons.append("no_baseline_model")

    if args.promote and not promotion_reasons:
        promotion_reasons.append("passed_all_gates")

    metadata = {
        "model_version": model_version,
        "trained_at": trained_at.isoformat(),
        "input": str(input_path),
        "training_row_count": int(len(df)),
        "data_window_start": df["feature_ts"].min().isoformat(),
        "data_window_end": df["feature_ts"].max().isoformat(),
        "feature_schema_version": schema["version"],
        "baseline_model_version": baseline_model_version,
        "promotion_decision": "promoted" if should_promote else "candidate_only",
        "promotion_reasons": promotion_reasons,
        "metrics": {
            "validation_auc": candidate_val_auc,
            "validation_recall": candidate_val_recall,
            "test_mae": candidate_test_mae,
            "feature_coverage_rate": feature_coverage,
        },
    }
    evaluation["baseline_comparison"] = baseline_comparison

    save_artifacts(candidate_dir, clf, reg, schema, metadata, evaluation)
    if should_promote:
        promote_candidate(candidate_dir, current_dir)

    print(
        json.dumps(
            {
                "model_version": model_version,
                "candidate_dir": str(candidate_dir),
                "promoted": should_promote,
                "promotion_reasons": promotion_reasons,
                "metrics": metadata["metrics"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
