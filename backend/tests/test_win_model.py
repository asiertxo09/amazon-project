from backend.ml import win_model


def _base_features() -> dict:
    return {
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
        "industry": "Fashion & Apparel",
        "source": "Inbound",
    }


def test_train_reports_holdout_metrics_above_chance():
    metrics = win_model.train()
    assert 0.5 < metrics["holdout_auc"] <= 1.0
    assert metrics["n_train"] > 0 and metrics["n_test"] > 0


def test_predict_returns_valid_contract_shape():
    result = win_model.predict(_base_features())
    assert 0 <= result["value_pct"] <= 100
    assert result["model"] == "logreg_v1"
    assert len(result["top_factors"]) == 3
    for factor in result["top_factors"]:
        assert factor["direction"] in ("+", "-")
        assert factor["factor"] in win_model.EXPLAINABLE_NUMERIC_FACTORS


def test_win_probability_moves_sensibly_on_synthetic_edge_cases():
    # Sanity-check monotonicity (PLAN.md §8a #2) — perturbing one variable at a
    # time toward a "worse" value should not increase win probability.
    base = win_model.predict(_base_features())["value_pct"]

    worse_geo_fit = dict(_base_features(), geo_fit_pct=0.2)
    assert win_model.predict(worse_geo_fit)["value_pct"] <= base

    worse_oversized = dict(_base_features(), oversized_pct=0.5)
    assert win_model.predict(worse_oversized)["value_pct"] <= base

    worse_price = dict(_base_features(), price_vs_incumbent_pct=40.0)
    assert win_model.predict(worse_price)["value_pct"] <= base

    better_geo_fit = dict(_base_features(), geo_fit_pct=0.99)
    assert win_model.predict(better_geo_fit)["value_pct"] >= base
