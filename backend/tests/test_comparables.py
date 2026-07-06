from backend.ml.comparables import find_comparables


def test_find_comparables_returns_k_results_sorted_by_distance():
    features = {
        "geo_fit_pct": 0.8,
        "daily_volume_serviceable": 2000,
        "avg_weight_kg": 2.0,
        "oversized_pct": 0.02,
        "pain_severity": 3,
        "price_vs_incumbent_pct": 5.0,
        "competitive_intensity": 3,
        "sales_cycle_touches": 8,
        "decision_time_days": 30,
        "contract_length_months": 24,
        "requires_intl": 0,
        "requires_pudo": 0,
        "requires_b2b": 0,
        "weekend_need": 1,
    }
    results = find_comparables(features, k=5)
    assert len(results) == 5
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances)
    for r in results:
        assert r["outcome"] in ("Won", "Lost")
