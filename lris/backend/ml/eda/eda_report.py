"""Automated EDA report generation.

Produces a static markdown report — not a runtime API dependency (per
ARCHITECTURE.md §1) — covering missing values, outliers, price
distribution, location statistics, feature correlations, and summary
stats for a given dataset version's clean data.
"""

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def generate_eda_report(clean_df: pd.DataFrame, output_path: Path) -> Path:
    """Generate a markdown EDA report for a cleaned dataset.

    Args:
        clean_df: Output of `feature_engineering.clean_for_training`.
        output_path: Where to write the markdown file.

    Returns:
        The path the report was written to.
    """
    sections = [
        "# EDA Report\n",
        _missing_values_section(clean_df),
        _outlier_section(clean_df),
        _price_distribution_section(clean_df),
        _location_stats_section(clean_df),
        _correlation_section(clean_df),
        _summary_stats_section(clean_df),
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(sections))
    logger.info("Wrote EDA report to %s", output_path)
    return output_path


def _missing_values_section(df: pd.DataFrame) -> str:
    missing = df.isna().sum()
    missing_pct = (missing / max(len(df), 1) * 100).round(2)
    lines = ["## Missing Values\n", "| Column | Missing | % |", "|---|---|---|"]
    for col in df.columns:
        lines.append(f"| {col} | {missing[col]} | {missing_pct[col]}% |")
    return "\n".join(lines) + "\n"


def _outlier_section(df: pd.DataFrame) -> str:
    lines = ["## Outlier Report (IQR method)\n", "| Column | Lower | Upper | Outliers |", "|---|---|---|---|"]
    for col in ["price", "size_marla", "price_per_marla"]:
        if col not in df.columns:
            continue
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = ((df[col] < lower) | (df[col] > upper)).sum()
        lines.append(f"| {col} | {lower:.2f} | {upper:.2f} | {outliers} |")
    return "\n".join(lines) + "\n"


def _price_distribution_section(df: pd.DataFrame) -> str:
    desc = df["price"].describe()
    lines = ["## Price Distribution\n", "```", desc.to_string(), "```"]
    return "\n".join(lines) + "\n"


def _location_stats_section(df: pd.DataFrame) -> str:
    if "location_id" not in df.columns:
        return ""
    stats = (
        df.groupby("location_id")["price_per_marla"]
        .agg(["mean", "median", "count"])
        .sort_values("count", ascending=False)
        .head(20)
    )
    lines = ["## Top 20 Locations by Listing Count\n", "```", stats.to_string(), "```"]
    return "\n".join(lines) + "\n"


def _correlation_section(df: pd.DataFrame) -> str:
    numeric_df = df.select_dtypes(include="number")
    corr = numeric_df.corr(numeric_only=True)
    lines = ["## Feature Correlations\n", "```", corr.round(2).to_string(), "```"]
    return "\n".join(lines) + "\n"


def _summary_stats_section(df: pd.DataFrame) -> str:
    lines = ["## Summary Statistics\n", "```", df.describe(include="all").to_string(), "```"]
    return "\n".join(lines) + "\n"
