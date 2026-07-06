"""Nearest-neighbor lookup over the 360-row historical dataset (PLAN.md §3b).

Not RAG — this is tabular data, so it uses sklearn.neighbors.NearestNeighbors
on standardized numeric features to retrieve the top-k most similar past
deals (with real outcomes) for the win-probability narrative's "comparable
customer profiles" claim.
"""
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from backend.ml.win_model import BOOLEAN_COLUMNS, NUMERIC_COLUMNS, load_dataframe

COMPARABLE_COLUMNS = NUMERIC_COLUMNS + BOOLEAN_COLUMNS

_cache: dict | None = None


def _get_index() -> dict:
    """Loads the dataframe and fits the scaler/NN index once per process,
    not on every request — the historical dataset doesn't change at runtime."""
    global _cache
    if _cache is None:
        df = load_dataframe()
        X = df[COMPARABLE_COLUMNS].values
        scaler = StandardScaler().fit(X)
        nn = NearestNeighbors(n_neighbors=min(10, len(df))).fit(scaler.transform(X))
        _cache = {"df": df, "scaler": scaler, "nn": nn}
    return _cache


def find_comparables(features: dict, k: int = 5) -> list[dict]:
    index = _get_index()
    df, scaler, nn = index["df"], index["scaler"], index["nn"]

    query = scaler.transform([[features.get(c) for c in COMPARABLE_COLUMNS]])
    distances, indices = nn.kneighbors(query, n_neighbors=k)

    results = []
    for i, dist in zip(indices[0], distances[0]):
        row = df.iloc[i]
        results.append(
            {
                "opportunity_id": row["opportunity_id"],
                "company_name": row["company_name"],
                "industry": row["industry"],
                "outcome": row["outcome"],
                "geo_fit_pct": row["geo_fit_pct"],
                "distance": float(dist),
            }
        )
    return results
