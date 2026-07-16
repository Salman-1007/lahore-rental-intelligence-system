"""Feature engineering: turns queried `Listing` rows into an ML-ready
DataFrame.

One deliberate design decision worth flagging: `price_per_marla` is
computed for EDA/reporting, but is NOT fed into the model as an input
feature, because it's derived directly from the target (`price`) and
would leak the answer. Instead, `location_price_encoding` is built from
`price_per_marla` using K-fold target encoding — each row's encoding is
computed from *other* rows only, which is what lets it generalize to
unseen combinations instead of memorizing.
"""

import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import KFold

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "size_marla",
    "property_type",
    "portion_type",
    "location_price_encoding",
    "bedrooms",
    "bathrooms",
    "parking_spaces",
    "is_furnished",
    "is_corner",
    "is_park_facing",
    "has_servant_quarter",
    "has_independent_entrance",
    "is_newly_built",
]
CATEGORICAL_FEATURES = ["property_type", "portion_type"]
TARGET_COLUMN = "price"


def build_raw_frame(listings: list) -> pd.DataFrame:
    """Flatten `Listing` ORM objects (with eager-loaded relations) into a DataFrame.

    Args:
        listings: `Listing` rows, each expected to have `.dimension` and
            `.property_details` already loaded (see
            `ListingRepository.get_with_details` / a bulk equivalent).

    Returns:
        One row per listing with the raw fields needed for downstream
        cleaning/feature engineering.
    """
    rows = []
    for listing in listings:
        if listing.dimension is None or listing.property_details is None:
            continue
        rows.append(
            {
                "listing_id": listing.id,
                "price": listing.current_price,
                "size_marla": listing.dimension.size_marla,
                "location_id": listing.location_id,
                "property_type": listing.property_details.property_type.value,
                "portion_type": listing.property_details.portion_type.value,
                "bedrooms": listing.property_details.bedrooms,
                "bathrooms": listing.property_details.bathrooms,
                "parking_spaces": listing.property_details.parking_spaces,
                "is_furnished": listing.property_details.is_furnished,
                "is_corner": listing.property_details.is_corner,
                "is_park_facing": listing.property_details.is_park_facing,
                "has_servant_quarter": listing.property_details.has_servant_quarter,
                "has_independent_entrance": listing.property_details.has_independent_entrance,
                "is_newly_built": listing.property_details.is_newly_built,
            }
        )
    return pd.DataFrame(rows)


def clean_for_training(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows unusable for training (missing price/size/location).

    Args:
        raw_df: Output of `build_raw_frame`.

    Returns:
        A copy with unusable rows removed and `price_per_marla` added
        (for EDA/reporting only — see module docstring).
    """
    df = raw_df.copy()
    df = df.dropna(subset=["price", "size_marla", "location_id"])
    df = df[(df["price"] > 0) & (df["size_marla"] > 0)]
    df["price_per_marla"] = df["price"] / df["size_marla"]
    df["bedrooms"] = df["bedrooms"].fillna(0)
    df["bathrooms"] = df["bathrooms"].fillna(0)
    return df.reset_index(drop=True)


def add_location_encoding(
    df: pd.DataFrame, n_folds: int = 5, smoothing: float = 10.0, random_state: int = 42
) -> pd.DataFrame:
    """Add a leakage-safe K-fold target-encoded `location_price_encoding` column.

    Each row's encoding is the smoothed mean `price_per_marla` for its
    location, computed using only the OTHER folds' rows — this is what
    lets a high-cardinality categorical like `location_id` be used as a
    single numeric feature without the model simply memorizing per-row
    answers.

    Args:
        df: Must already have `price_per_marla` (see `clean_for_training`).
        n_folds: Number of K-fold splits used for out-of-fold encoding.
        smoothing: Higher values pull sparse locations' encoding closer to
            the global mean, reducing overfitting on locations with very
            few listings.
        random_state: Seed for reproducible fold assignment.

    Returns:
        `df` with a new `location_price_encoding` column.
    """
    df = df.copy()
    global_mean = df["price_per_marla"].mean()
    df["location_price_encoding"] = global_mean

    kfold = KFold(n_splits=min(n_folds, len(df)), shuffle=True, random_state=random_state)

    for train_idx, holdout_idx in kfold.split(df):
        train_fold = df.iloc[train_idx]
        stats = train_fold.groupby("location_id")["price_per_marla"].agg(["mean", "count"])
        smoothed = (stats["mean"] * stats["count"] + global_mean * smoothing) / (
            stats["count"] + smoothing
        )
        df.loc[df.index[holdout_idx], "location_price_encoding"] = (
            df.iloc[holdout_idx]["location_id"].map(smoothed).fillna(global_mean).values
        )

    return df


def build_location_encoding_map(
    df: pd.DataFrame, smoothing: float = 10.0
) -> dict[int, float]:
    """Build the final location_id -> encoding map for use at inference time.

    Unlike `add_location_encoding` (which is leakage-safe for *training*),
    inference has no leakage concern — a new prediction request isn't in
    the training set — so this uses the full dataset for the best
    possible estimate per location.

    Args:
        df: Must already have `price_per_marla`.
        smoothing: Same smoothing constant used in `add_location_encoding`,
            kept consistent so train/inference encodings are comparable.

    Returns:
        Mapping of `location_id` -> smoothed mean price-per-marla.
    """
    global_mean = df["price_per_marla"].mean()
    stats = df.groupby("location_id")["price_per_marla"].agg(["mean", "count"])
    smoothed = (stats["mean"] * stats["count"] + global_mean * smoothing) / (
        stats["count"] + smoothing
    )
    encoding_map = smoothed.to_dict()
    encoding_map["__global_mean__"] = global_mean
    return encoding_map


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Select and order the final model-input columns plus the target.

    Args:
        df: Output of `clean_for_training` + `add_location_encoding`.

    Returns:
        DataFrame containing exactly `FEATURE_COLUMNS + [TARGET_COLUMN]`.
    """
    return df[FEATURE_COLUMNS + [TARGET_COLUMN]].reset_index(drop=True)
