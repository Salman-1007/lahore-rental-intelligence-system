"""Unit tests for feature engineering.

The DataFrame built here is synthetic test fixture data used only to
verify the encoding/leakage-prevention mechanics - it is never presented
as real listing data anywhere in the product.
"""

import pandas as pd

from ml.features.feature_engineering import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    add_location_encoding,
    build_feature_frame,
    build_location_encoding_map,
    clean_for_training,
)


def _synthetic_raw_df() -> pd.DataFrame:
    rows = []
    for i in range(30):
        location_id = 1 if i % 2 == 0 else 2
        base_price = 40000 if location_id == 1 else 60000
        rows.append(
            {
                "listing_id": i,
                "price": base_price + (i * 100),
                "size_marla": 5 + (i % 5),
                "location_id": location_id,
                "property_type": "portion",
                "portion_type": "upper_portion",
                "bedrooms": 2,
                "bathrooms": 1,
                "parking_spaces": 1,
                "is_furnished": False,
                "is_corner": False,
                "is_park_facing": False,
                "has_servant_quarter": False,
                "has_independent_entrance": False,
                "is_newly_built": False,
            }
        )
    return pd.DataFrame(rows)


def test_clean_for_training_drops_invalid_rows() -> None:
    df = _synthetic_raw_df()
    df.loc[0, "price"] = -1
    df.loc[1, "location_id"] = None

    cleaned = clean_for_training(df)
    assert (cleaned["price"] > 0).all()
    assert cleaned["location_id"].notna().all()
    assert "price_per_marla" in cleaned.columns


def test_add_location_encoding_differentiates_by_location() -> None:
    cleaned = clean_for_training(_synthetic_raw_df())
    encoded = add_location_encoding(cleaned, n_folds=3)

    mean_loc_1 = encoded[encoded["location_id"] == 1]["location_price_encoding"].mean()
    mean_loc_2 = encoded[encoded["location_id"] == 2]["location_price_encoding"].mean()
    assert mean_loc_2 > mean_loc_1


def test_build_feature_frame_has_expected_columns() -> None:
    cleaned = clean_for_training(_synthetic_raw_df())
    encoded = add_location_encoding(cleaned, n_folds=3)
    features = build_feature_frame(encoded)

    assert list(features.columns) == FEATURE_COLUMNS + [TARGET_COLUMN]
    for col in CATEGORICAL_FEATURES:
        assert col in features.columns


def test_location_encoding_map_includes_global_mean_fallback() -> None:
    cleaned = clean_for_training(_synthetic_raw_df())
    encoding_map = build_location_encoding_map(cleaned)

    assert "__global_mean__" in encoding_map
    assert 1 in encoding_map
    assert 2 in encoding_map
