"""Dataset versioning: raw -> clean -> processed -> training/validation.

Never trains directly on scraped data (RULES.md §5). Every call to
`build_dataset` creates a brand-new timestamped version directory under
each stage folder and never overwrites a previous version, so any trained
model can always point back at the exact data that produced it.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.listing import Listing
from ml.features.feature_engineering import (
    add_location_encoding,
    build_feature_frame,
    build_location_encoding_map,
    build_raw_frame,
    clean_for_training,
)

logger = logging.getLogger(__name__)


@dataclass
class DatasetVersion:
    """Everything a training run needs to know about one dataset build."""

    version: str
    raw_path: Path
    clean_path: Path
    processed_path: Path
    training_path: Path
    validation_path: Path
    location_encoding_path: Path
    row_counts: dict[str, int]


def build_dataset(
    session: Session, output_root: Path, test_size: float = 0.2, random_state: int = 42
) -> DatasetVersion:
    """Build a new, immutable, timestamped dataset version from the DB.

    Args:
        session: Active DB session to query listings from.
        output_root: Root `data/` directory (contains raw/clean/processed/
            training/validation subfolders).
        test_size: Fraction of processed rows held out for validation.
        random_state: Seed for the train/validation split.

    Returns:
        A `DatasetVersion` describing every path and row count produced.

    Raises:
        ValueError: If there are too few usable listings to build a
            meaningful dataset (fewer than 20 rows after cleaning).
    """
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    stmt = select(Listing).where(Listing.is_active.is_(True)).options(
        selectinload(Listing.dimension), selectinload(Listing.property_details)
    )
    listings = list(session.execute(stmt).scalars().all())

    raw_df = build_raw_frame(listings)
    raw_path = _write_versioned(output_root / "raw" / version, "listings.parquet", raw_df)

    clean_df = clean_for_training(raw_df)
    if len(clean_df) < 20:
        raise ValueError(
            f"Only {len(clean_df)} usable listings after cleaning; need at least 20 "
            "to build a meaningful dataset. Scrape more data first."
        )
    clean_path = _write_versioned(output_root / "clean" / version, "listings.parquet", clean_df)

    encoded_df = add_location_encoding(clean_df)
    processed_df = build_feature_frame(encoded_df)
    processed_path = _write_versioned(
        output_root / "processed" / version, "features.parquet", processed_df
    )

    train_df, val_df = train_test_split(
        processed_df, test_size=test_size, random_state=random_state
    )
    training_path = _write_versioned(
        output_root / "training" / version, "train.parquet", train_df
    )
    validation_path = _write_versioned(
        output_root / "validation" / version, "validation.parquet", val_df
    )

    location_encoding_map = build_location_encoding_map(clean_df)
    location_encoding_path = output_root / "processed" / version / "location_encoding.json"
    location_encoding_path.write_text(
        json.dumps({str(k): v for k, v in location_encoding_map.items()}, indent=2)
    )

    row_counts = {
        "raw": len(raw_df),
        "clean": len(clean_df),
        "processed": len(processed_df),
        "training": len(train_df),
        "validation": len(val_df),
    }

    _write_metadata(output_root, version, row_counts)

    logger.info("Built dataset version %s: %s", version, row_counts)

    return DatasetVersion(
        version=version,
        raw_path=raw_path,
        clean_path=clean_path,
        processed_path=processed_path,
        training_path=training_path,
        validation_path=validation_path,
        location_encoding_path=location_encoding_path,
        row_counts=row_counts,
    )


def _write_versioned(directory: Path, filename: str, df: pd.DataFrame) -> Path:
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / filename
    df.to_parquet(path, index=False)
    return path


def _write_metadata(output_root: Path, version: str, row_counts: dict[str, int]) -> None:
    metadata = {
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "row_counts": row_counts,
    }
    metadata_path = output_root / "processed" / version / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))


def load_dataset_version(
    output_root: Path, version: str
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load a previously built dataset version's train/validation splits.

    Args:
        output_root: Root `data/` directory.
        version: The version timestamp string returned by `build_dataset`.

    Returns:
        `(train_df, validation_df, location_encoding_map)`.
    """
    train_df = pd.read_parquet(output_root / "training" / version / "train.parquet")
    val_df = pd.read_parquet(output_root / "validation" / version / "validation.parquet")
    encoding_map = json.loads(
        (output_root / "processed" / version / "location_encoding.json").read_text()
    )
    return train_df, val_df, encoding_map
