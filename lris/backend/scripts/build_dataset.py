"""CLI entrypoint: build a new versioned dataset from the database, plus
its EDA report.

Usage (from backend/):
    python -m scripts.build_dataset
"""

import argparse
import logging

import pandas as pd

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.session import session_scope
from ml.datasets.dataset_builder import build_dataset
from ml.eda.eda_report import generate_eda_report

configure_logging()
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a new LRIS dataset version.")
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    settings = get_settings()

    with session_scope() as session:
        dataset_version = build_dataset(session, settings.data_dir, test_size=args.test_size)

    print(f"Dataset version: {dataset_version.version}")
    print(f"Row counts: {dataset_version.row_counts}")

    clean_df = pd.read_parquet(dataset_version.clean_path)
    eda_path = settings.data_dir / "processed" / dataset_version.version / "eda_report.md"
    generate_eda_report(clean_df, eda_path)
    print(f"EDA report: {eda_path}")
    print(f"\nTrain your model with:\n  python -m ml.training.train {dataset_version.version}")


if __name__ == "__main__":
    main()
