"""CatBoost training pipeline.

Trains three models per run: a main RMSE-loss regressor for the point
estimate, and two quantile regressors (alpha=0.1 / alpha=0.9) that give
the `/predict` endpoint a real, model-based confidence range instead of a
hand-waved +/- percentage. All three share the same features and the same
dataset version, so they stay consistent with each other.

This module is meant to be run on a machine with real scraped data and
enough compute for CatBoost - see the `if __name__ == "__main__"` CLI
entrypoint at the bottom.
"""

import itertools
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool
from sklearn.model_selection import KFold

from ml.datasets.dataset_builder import load_dataset_version
from ml.evaluation.evaluate import compute_metrics, write_evaluation_report
from ml.features.feature_engineering import CATEGORICAL_FEATURES, FEATURE_COLUMNS, TARGET_COLUMN

logger = logging.getLogger(__name__)

_HYPERPARAM_GRID = {
    "depth": [4, 6, 8],
    "learning_rate": [0.03, 0.05, 0.1],
    "l2_leaf_reg": [1, 3, 5],
}


@dataclass
class TrainedModelPaths:
    """Where a training run's artifacts ended up."""

    model_dir: Path
    main_model_path: Path
    lower_model_path: Path
    upper_model_path: Path
    metadata_path: Path
    evaluation_path: Path


def _prepare_X(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURE_COLUMNS].copy()
    for col in CATEGORICAL_FEATURES:
        X[col] = X[col].astype(str)
    return X


def _to_pool(df: pd.DataFrame) -> Pool:
    X = _prepare_X(df)
    y = df[TARGET_COLUMN]
    cat_indices = [X.columns.get_loc(c) for c in CATEGORICAL_FEATURES]
    return Pool(X, y, cat_features=cat_indices)


def _cross_validate_params(train_df: pd.DataFrame, params: dict, n_folds: int = 4) -> float:
    """Return mean validation RMSE for one hyperparameter combination."""
    kfold = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    fold_rmses = []

    for fold_train_idx, fold_val_idx in kfold.split(train_df):
        fold_train = train_df.iloc[fold_train_idx]
        fold_val = train_df.iloc[fold_val_idx]

        model = CatBoostRegressor(loss_function="RMSE", verbose=False, random_seed=42, **params)
        model.fit(_to_pool(fold_train), eval_set=_to_pool(fold_val), early_stopping_rounds=30)
        preds = model.predict(_prepare_X(fold_val))
        rmse = float(np.sqrt(np.mean((fold_val[TARGET_COLUMN].values - preds) ** 2)))
        fold_rmses.append(rmse)

    return float(np.mean(fold_rmses))


def _search_best_params(train_df: pd.DataFrame, max_combinations: int = 9) -> dict:
    """Search a small grid of CatBoost hyperparameters via K-fold CV.

    Args:
        train_df: Training split (features + target).
        max_combinations: Cap on grid combinations tried, keeping a full
            run tractable on a laptop.

    Returns:
        The hyperparameter dict with the lowest mean CV RMSE.
    """
    keys = list(_HYPERPARAM_GRID.keys())
    all_combos = list(itertools.product(*_HYPERPARAM_GRID.values()))
    combos = all_combos[:max_combinations]

    best_params = None
    best_rmse = float("inf")

    for combo in combos:
        params = dict(zip(keys, combo))
        rmse = _cross_validate_params(train_df, params)
        logger.info("params=%s -> CV RMSE=%.2f", params, rmse)
        if rmse < best_rmse:
            best_rmse = rmse
            best_params = params

    logger.info("Best params: %s (CV RMSE=%.2f)", best_params, best_rmse)
    return best_params


def _fit_final_model(
    train_df: pd.DataFrame, val_df: pd.DataFrame, params: dict, loss_function: str = "RMSE"
) -> CatBoostRegressor:
    model = CatBoostRegressor(loss_function=loss_function, verbose=False, random_seed=42, **params)
    model.fit(_to_pool(train_df), eval_set=_to_pool(val_df), early_stopping_rounds=50)
    return model


def train_model(
    dataset_version: str,
    data_root: Path = Path("data"),
    models_root: Path = Path("ml/models_registry"),
) -> TrainedModelPaths:
    """Train the main + quantile models for one dataset version.

    Args:
        dataset_version: A version string previously produced by
            `dataset_builder.build_dataset`.
        data_root: Root `data/` directory.
        models_root: Root directory model artifacts are written under.

    Returns:
        Paths to every artifact this run produced.
    """
    train_df, val_df, _encoding_map = load_dataset_version(data_root, dataset_version)

    best_params = _search_best_params(train_df)

    main_model = _fit_final_model(train_df, val_df, best_params, loss_function="RMSE")
    lower_model = _fit_final_model(train_df, val_df, best_params, loss_function="Quantile:alpha=0.1")
    upper_model = _fit_final_model(train_df, val_df, best_params, loss_function="Quantile:alpha=0.9")

    preds = main_model.predict(_prepare_X(val_df))
    metrics = compute_metrics(val_df[TARGET_COLUMN].values, preds)

    model_version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_dir = models_root / model_version
    model_dir.mkdir(parents=True, exist_ok=False)

    main_path = model_dir / "main_model.cbm"
    lower_path = model_dir / "lower_model.cbm"
    upper_path = model_dir / "upper_model.cbm"
    main_model.save_model(str(main_path))
    lower_model.save_model(str(lower_path))
    upper_model.save_model(str(upper_path))

    metadata = {
        "model_version": model_version,
        "dataset_version": dataset_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "params": best_params,
        "feature_columns": FEATURE_COLUMNS,
        "categorical_features": CATEGORICAL_FEATURES,
    }
    metadata_path = model_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    evaluation_path = write_evaluation_report(
        metrics, model_dir / "evaluation_report.json", dataset_version, best_params
    )

    return TrainedModelPaths(
        model_dir=model_dir,
        main_model_path=main_path,
        lower_model_path=lower_path,
        upper_model_path=upper_path,
        metadata_path=metadata_path,
        evaluation_path=evaluation_path,
    )


def get_latest_model_dir(models_root: Path = Path("ml/models_registry")) -> Path | None:
    """Return the most recently trained model's directory, or None if none exist."""
    if not models_root.exists():
        return None
    candidates = [d for d in models_root.iterdir() if d.is_dir() and (d / "metadata.json").exists()]
    if not candidates:
        return None
    return max(candidates, key=lambda d: d.name)


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO)

    arg_parser = argparse.ArgumentParser(description="Train the LRIS rent estimation model.")
    arg_parser.add_argument("dataset_version", help="Dataset version string to train on.")
    arg_parser.add_argument("--data-root", default="data")
    arg_parser.add_argument("--models-root", default="ml/models_registry")
    args = arg_parser.parse_args()

    result = train_model(args.dataset_version, Path(args.data_root), Path(args.models_root))
    print(f"Model trained: {result.model_dir}")
    sys.exit(0)
