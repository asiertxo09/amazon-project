"""Deterministic pricing engine — no LLM involved (PLAN.md §3a).

Looks up First/Middle/Home-delivery mile costs by (volume tier x weight band),
adds fixed overhead (FX-converted), applies region multiplier, and checks
contribution-margin guardrails.
"""
import json
from pathlib import Path
from typing import Literal

DATA_PATH = Path(__file__).resolve().parent / "data" / "pricing_tables.json"
_TABLES = json.loads(DATA_PATH.read_text())

WEIGHT_BAND_UPPER_KG = [0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 9, 12, 15, 18, 21, 24, 27, 30]
WEIGHT_BANDS = _TABLES["weight_bands"]
assert len(WEIGHT_BAND_UPPER_KG) == len(WEIGHT_BANDS)

VOLUME_TIER_UPPER = [200, 300, 400, 500, 700, 900, 1200, 1500, 2000, 3000, 4000, None]
VOLUME_TIERS = _TABLES["volume_tiers"]
assert len(VOLUME_TIER_UPPER) == len(VOLUME_TIERS)

FIXED_OVERHEAD_USD = _TABLES["fixed_overhead_usd_per_parcel"]
FX_RATE = _TABLES["usd_to_eur_fx_rate"]
REGION_MULTIPLIER = _TABLES["region_multiplier"]
PREMIUM_ADDONS_EUR = _TABLES["premium_addons_eur"]
GUARDRAILS = _TABLES["guardrails"]

Region = Literal["peninsula", "balearic_islands"]

MAX_SERVICEABLE_WEIGHT_KG = 15
MAX_SERVICEABLE_DIMENSION_CM = (80, 80, 60)


def weight_band_for(weight_kg: float) -> str:
    for upper, band in zip(WEIGHT_BAND_UPPER_KG, WEIGHT_BANDS):
        if weight_kg <= upper:
            return band
    return WEIGHT_BANDS[-1]


def volume_tier_for(daily_volume: float) -> str:
    for upper, tier in zip(VOLUME_TIER_UPPER, VOLUME_TIERS):
        if upper is None or daily_volume <= upper:
            return tier
    return VOLUME_TIERS[-1]


def is_serviceable_parcel(weight_kg: float, dimensions_cm: tuple[float, float, float] | None = None) -> bool:
    if weight_kg > MAX_SERVICEABLE_WEIGHT_KG:
        return False
    if dimensions_cm is not None:
        if any(d > m for d, m in zip(sorted(dimensions_cm, reverse=True), sorted(MAX_SERVICEABLE_DIMENSION_CM, reverse=True))):
            return False
    return True


def is_serviceable_demand(
    *, region: str, requires_pudo: bool = False, requires_intl: bool = False, requires_b2b: bool = False
) -> bool:
    """Mirrors the historical dataset's own serviceable-volume logic (PLAN.md §3a)."""
    if region not in REGION_MULTIPLIER:
        return False
    if requires_pudo or requires_intl or requires_b2b:
        return False
    return True


def unit_cost_eur(daily_volume: float, weight_kg: float, region: Region = "peninsula") -> float:
    tier = volume_tier_for(daily_volume)
    band = weight_band_for(weight_kg)
    fm = _TABLES["first_mile_cost"][tier][band]
    mm = _TABLES["middle_mile_cost"][tier][band]
    hd = _TABLES["home_delivery_cost"][tier][band]
    overhead_eur = FIXED_OVERHEAD_USD / FX_RATE
    base_eur = fm + mm + hd + overhead_eur
    return base_eur * REGION_MULTIPLIER[region]


def price_for_margin(unit_cost: float, margin_pct: float) -> float:
    """Price such that (price - cost) / price == margin_pct / 100."""
    if margin_pct >= 100:
        raise ValueError("margin_pct must be < 100")
    return unit_cost / (1 - margin_pct / 100)


def margin_pct_for_price(unit_cost: float, price: float) -> float:
    if price <= 0:
        raise ValueError("price must be > 0")
    return (price - unit_cost) / price * 100


def guardrail_status(margin_pct: float) -> Literal["ok", "vp_approval_required", "no_go"]:
    if margin_pct < GUARDRAILS["automatic_no_go_below_pct"]:
        return "no_go"
    if margin_pct < GUARDRAILS["vp_approval_required_below_pct"]:
        return "vp_approval_required"
    return "ok"


def pricing_scenarios(unit_cost: float) -> list[dict]:
    """Aggressive/Balanced/Conservative scenarios, all guardrail-compliant (>= 13% floor)."""
    floor = GUARDRAILS["minimum_contribution_margin_pct"]
    target = GUARDRAILS["target_contribution_margin_pct"]
    midpoint = (floor + target) / 2
    scenarios = []
    for name, margin_pct in [("Aggressive", floor + 1), ("Balanced", midpoint), ("Conservative", target)]:
        price = price_for_margin(unit_cost, margin_pct)
        scenarios.append(
            {
                "name": name,
                "margin_pct": round(margin_pct, 2),
                "avg_price_per_parcel_eur": round(price, 2),
                "guardrail_status": guardrail_status(margin_pct),
            }
        )
    return scenarios
