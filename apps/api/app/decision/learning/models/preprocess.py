"""Shared sklearn preprocessing. Missing values are imputed, not dropped silently."""

from typing import Any

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from app.decision.learning.features import CATEGORICAL_FEATURES, NUMERIC_FEATURES

NUMERIC_COUNT = len(NUMERIC_FEATURES)


def dicts_to_matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    """Convert feature dicts to a mixed object matrix. Picklable for joblib."""
    matrix: list[list[Any]] = []
    for row in rows:
        values: list[Any] = []
        for name in NUMERIC_FEATURES:
            value = row.get(name)
            values.append(np.nan if value is None or value == "" else float(value))
        for name in CATEGORICAL_FEATURES:
            value = row.get(name)
            values.append("NA" if value in (None, "") else str(value))
        matrix.append(values)
    if not matrix:
        return np.empty((0, len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES)))
    return np.asarray(matrix, dtype=object)


def transformed_feature_names(columns: ColumnTransformer) -> list[str]:
    encoder = columns.named_transformers_["cat"].named_steps["encode"]
    return [
        *NUMERIC_FEATURES,
        *encoder.get_feature_names_out(list(CATEGORICAL_FEATURES)),
    ]


def feature_preprocessor(*, scale: bool) -> Pipeline:
    numeric_steps: list[tuple[str, object]] = [
        ("impute", SimpleImputer(strategy="median")),
    ]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            (
                "encode",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    columns = ColumnTransformer(
        [
            ("num", numeric, list(range(NUMERIC_COUNT))),
            (
                "cat",
                categorical,
                list(
                    range(
                        NUMERIC_COUNT,
                        NUMERIC_COUNT + len(CATEGORICAL_FEATURES),
                    )
                ),
            ),
        ]
    )
    return Pipeline(
        [
            ("to_matrix", FunctionTransformer(dicts_to_matrix, validate=False)),
            ("columns", columns),
        ]
    )
