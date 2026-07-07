"""Win-probability classifier trained on the 360-row historical dataset (PLAN.md §3a).

Logistic regression, not an LLM prompt — the LLM layer only narrates this
model's output. Excludes outcome-dependent columns (lost_reason,
final_margin_pct) and identifiers (opportunity_id, company_name) as features
to avoid leakage.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "historical_opportunities.csv"
MODEL_PATH = Path(__file__).resolve().parent / "win_model.joblib"

BOOLEAN_COLUMNS = ["requires_intl", "requires_pudo", "requires_b2b", "weekend_need"]
NUMERIC_COLUMNS = [
    "geo_fit_pct",
    "daily_volume_serviceable",
    "avg_weight_kg",
    "oversized_pct",
    "pain_severity",
    "price_vs_incumbent_pct",
    "competitive_intensity",
    "sales_cycle_touches",
    "decision_time_days",
    "contract_length_months",
]
CATEGORICAL_COLUMNS = ["industry", "source"]
FEATURE_COLUMNS = NUMERIC_COLUMNS + BOOLEAN_COLUMNS + CATEGORICAL_COLUMNS
TARGET_COLUMN = "outcome"

# Restricting "top factors" explanations to these named, directly interpretable
# signals — the ones the Contract's example (geo_fit_pct, oversized_pct, ...)
# expects — rather than exploding one-hot categorical dummies into the output.
EXPLAINABLE_NUMERIC_FACTORS = NUMERIC_COLUMNS + BOOLEAN_COLUMNS


def load_dataframe() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    for col in BOOLEAN_COLUMNS:
        df[col] = df[col].map({"Yes": 1, "No": 0})
    df["label"] = (df[TARGET_COLUMN] == "Won").astype(int)
    return df


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_COLUMNS + BOOLEAN_COLUMNS),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLUMNS),
        ]
    )
    clf = LogisticRegression(max_iter=1000, C=1.0)
    return Pipeline([("preprocess", preprocessor), ("clf", clf)])


def train() -> dict:
    df = load_dataframe()
    X = df[FEATURE_COLUMNS]
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    proba_test = pipeline.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= 0.5).astype(int)
    metrics = {
        "holdout_auc": roc_auc_score(y_test, proba_test),
        "holdout_accuracy": accuracy_score(y_test, pred_test),
        "n_train": len(X_train),
        "n_test": len(X_test),
    }

    joblib.dump({"pipeline": pipeline, "metrics": metrics}, MODEL_PATH)
    return metrics


_bundle_cache: dict | None = None


def _load_bundle() -> dict:
    global _bundle_cache
    if _bundle_cache is None:
        if not MODEL_PATH.exists():
            train()
        _bundle_cache = joblib.load(MODEL_PATH)
    return _bundle_cache


def predict(features: dict) -> dict:
    """features: dict with keys = FEATURE_COLUMNS (booleans as 0/1 or True/False)."""
    bundle = _load_bundle()
    pipeline: Pipeline = bundle["pipeline"]

    row = {col: features.get(col) for col in FEATURE_COLUMNS}
    X = pd.DataFrame([row])
    proba_win = pipeline.predict_proba(X)[0, 1]

    top_factors = _top_factors(pipeline, row)
    return {
        "value_pct": round(proba_win * 100),
        "model": "logreg_v1",
        "top_factors": top_factors,
        "metrics": bundle["metrics"],
    }


def _top_factors(pipeline: Pipeline, row: dict, n: int = 3) -> list[dict]:
    preprocessor: ColumnTransformer = pipeline.named_steps["preprocess"]
    clf: LogisticRegression = pipeline.named_steps["clf"]

    scaler: StandardScaler = preprocessor.named_transformers_["num"]
    numeric_cols = NUMERIC_COLUMNS + BOOLEAN_COLUMNS
    scaled_values = scaler.transform(pd.DataFrame([{c: row[c] for c in numeric_cols}]))[0]

    n_numeric = len(numeric_cols)
    numeric_coefs = clf.coef_[0][:n_numeric]

    contributions = [
        (col, scaled_values[i] * numeric_coefs[i]) for i, col in enumerate(numeric_cols)
    ]
    contributions.sort(key=lambda t: abs(t[1]), reverse=True)

    return [
        {"factor": col, "direction": "+" if contribution > 0 else "-"}
        for col, contribution in contributions[:n]
    ]


if __name__ == "__main__":
    print(train())
