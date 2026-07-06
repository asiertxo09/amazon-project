import math

import pytest

from backend import pricing


def test_unit_cost_peninsula_hand_computed():
    # daily_volume=850 -> tier "701-900"; weight=2.3kg -> band "2-2.5kg"
    # fm=1.17, mm=1.02, hd=1.28 (EUR), overhead = 0.17/1.16 EUR
    expected = 1.17 + 1.02 + 1.28 + (0.17 / 1.16)
    got = pricing.unit_cost_eur(daily_volume=850, weight_kg=2.3, region="peninsula")
    assert got == pytest.approx(expected, rel=1e-9)


def test_unit_cost_balearic_applies_1_35_multiplier():
    peninsula = pricing.unit_cost_eur(daily_volume=850, weight_kg=2.3, region="peninsula")
    balearic = pricing.unit_cost_eur(daily_volume=850, weight_kg=2.3, region="balearic_islands")
    assert balearic == pytest.approx(peninsula * 1.35, rel=1e-9)


def test_volume_tier_and_weight_band_boundaries():
    assert pricing.volume_tier_for(200) == "0-200"
    assert pricing.volume_tier_for(201) == "201-300"
    assert pricing.volume_tier_for(5000) == "4000+"
    assert pricing.weight_band_for(0.25) == "0-0.25kg"
    assert pricing.weight_band_for(0.26) == "0.25-0.5kg"
    assert pricing.weight_band_for(30) == "27-30kg"


def test_price_for_margin_round_trips_to_same_margin():
    cost = 3.62
    price = pricing.price_for_margin(cost, 17.5)
    assert pricing.margin_pct_for_price(cost, price) == pytest.approx(17.5, rel=1e-9)


def test_guardrail_status_thresholds():
    assert pricing.guardrail_status(21) == "ok"
    assert pricing.guardrail_status(13) == "ok"
    assert pricing.guardrail_status(12.9) == "vp_approval_required"
    assert pricing.guardrail_status(9) == "vp_approval_required"
    assert pricing.guardrail_status(8.9) == "no_go"


def test_all_three_scenarios_respect_13pct_floor():
    cost = pricing.unit_cost_eur(daily_volume=850, weight_kg=2.3, region="peninsula")
    scenarios = pricing.pricing_scenarios(cost)
    assert len(scenarios) == 3
    for s in scenarios:
        assert s["margin_pct"] >= 13.0
        assert s["guardrail_status"] == "ok"
        assert s["avg_price_per_parcel_eur"] > cost


def test_is_serviceable_parcel_excludes_oversized():
    assert pricing.is_serviceable_parcel(14.9) is True
    assert pricing.is_serviceable_parcel(15.1) is False
    assert pricing.is_serviceable_parcel(10, dimensions_cm=(80, 80, 60)) is True
    assert pricing.is_serviceable_parcel(10, dimensions_cm=(90, 80, 60)) is False


def test_is_serviceable_demand_excludes_intl_pudo_b2b_and_bad_region():
    assert pricing.is_serviceable_demand(region="peninsula") is True
    assert pricing.is_serviceable_demand(region="balearic_islands") is True
    assert pricing.is_serviceable_demand(region="portugal") is False
    assert pricing.is_serviceable_demand(region="peninsula", requires_pudo=True) is False
    assert pricing.is_serviceable_demand(region="peninsula", requires_intl=True) is False
    assert pricing.is_serviceable_demand(region="peninsula", requires_b2b=True) is False
