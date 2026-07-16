"""Evaluation: standard regression metrics for the rent model.

Kept separate from `training/` so metric computation can be reused for
the persisted evaluation report, ad-hoc model comparison, and (later)
monitoring model drift without depending on training-specific code.
"""

import json
import logging
from pathlib import Path

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score

logger = logging.getLogger(__name__)


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute MAE, RMSE, R², and MAPE for a set of predictions.

    Args:
        y_true: Actual target values.
        y_pred: Model predictions.

    Returns:
        Dict with keys `mae`, `rmse`, `r2`, `mape`.
    """
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(np.mean((np.asarray(y_true) - np.asarray(y_pred)) ** 2)))
    r2 = r2_score(y_true, y_pred)
    mape = mean_absolute_percentage_error(y_true, y_pred)
    return {"mae": float(mae), "rmse": rmse, "r2": float(r2), "mape": float(mape)}


def write_evaluation_report(
    metrics: dict[str, float], output_path: Path, dataset_version: str, model_params: dict
) -> Path:
    """Persist an evaluation report alongside a trained model artifact.

    Args:
        metrics: Output of `compute_metrics`.
        output_path: Where to write the JSON report.
        dataset_version: The dataset version this model was trained on
            (for lineage — every model must know which data produced it).
        model_params: The hyperparameters the model was trained with.

    Returns:
        The path the report was written to.
    """
    report = {
        "dataset_version": dataset_version,
        "model_params": model_params,
        "metrics": metrics,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))
    logger.info("Wrote evaluation report to %s: %s", output_path, metrics)
    return output_path
