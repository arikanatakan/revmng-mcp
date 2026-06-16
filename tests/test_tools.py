import json

import pytest

from revmng_mcp import _tools as t
from revmng_mcp._tools import DemandModelInput, FareClassInput, MetricsInput, ProductInput

CLASSES = [FareClassInput(fare=1000, mean=30, sd=12),
           FareClassInput(fare=700, mean=40, sd=15),
           FareClassInput(fare=400, mean=60, sd=20)]


def test_protection_levels_emsr_b():
    r = t.protection_levels(CLASSES, 120)
    assert r["method"] == "EMSR-b"
    assert r["booking_limits_int"][0] == 120
    assert "summary" in r


def test_protection_levels_optimal_has_expected_revenue():
    r = t.protection_levels(CLASSES, 120, method="optimal")
    assert r["method"] == "optimal (DP)"
    assert r["expected_revenue"] is not None


def test_protection_levels_bad_method():
    r = t.protection_levels(CLASSES, 120, method="nope")
    assert "error" in r and "hint" in r


def test_overbooking_service_and_cost():
    s = t.overbooking_limit(100, 0.1)
    assert s["authorization_limit"] == 111
    c = t.overbooking_limit(100, 0.12, denied_cost=400, spoilage_cost=120)
    assert c["method"] == "cost"


def test_newsvendor():
    r = t.newsvendor(10, 4, 100, 30)
    assert r["critical_ratio"] == pytest.approx(0.6)


def test_optimal_price_linear():
    r = t.optimal_price(DemandModelInput(model="linear", intercept=100, slope=2),
                        unit_cost=10)
    assert r["optimal_price"] == pytest.approx(30.0)


def test_optimal_price_missing_params():
    r = t.optimal_price(DemandModelInput(model="linear"))
    assert "error" in r


def test_revenue_opportunity():
    r = t.revenue_opportunity([1000, 800, 600, 200], [25, 30, 20, 50], 100,
                              booking_limits=[100, 70, 45, 32])
    assert r["rom"] == pytest.approx(0.66, abs=0.005)


def test_evaluate_group_from_scenario():
    r = t.evaluate_group(60, 90, variable_cost=50, group_size=30, capacity=100,
                         demand=[70, 95, 85], value_per_unit=70)
    assert r["displacement_cost"] == pytest.approx(2800)
    assert r["accept"] is False


def test_evaluate_group_needs_inputs():
    assert "error" in t.evaluate_group(60, 90)


def test_evaluate_stay():
    r = t.evaluate_stay({"Mon": 80, "Tue": 120, "Wed": 90},
                        ["Mon", "Tue", "Wed"], 320)
    assert r["accept"] is True
    assert r["hurdle"] == pytest.approx(290)


def test_metrics():
    r = t.metrics(MetricsInput(room_revenue=18000, rooms_sold=75, available_rooms=100))
    assert r["metrics"]["revpar"] == pytest.approx(180)
    assert r["metrics"]["occupancy"] == pytest.approx(0.75)


def test_metrics_empty():
    assert "error" in t.metrics(MetricsInput())


def test_describe_inputs():
    d = t.describe_inputs()
    assert d["definitions"] and d["methods"]


def test_bid_prices():
    pytest.importorskip("scipy")
    r = t.bid_prices([ProductInput(fare=200, uses={"R": 1}, demand=60),
                      ProductInput(fare=100, uses={"R": 1}, demand=80)], {"R": 100})
    assert r["bid_prices"]["R"] == pytest.approx(100.0)


def test_payload_is_json_serializable():
    json.dumps(t.protection_levels(CLASSES, 120))
    json.dumps(t.newsvendor(10, 4, 100, 30))


def test_charts_return_png_bytes():
    pytest.importorskip("scipy")
    pngs = [
        t.protection_png(CLASSES, 120),
        t.protection_png(CLASSES, 120, kind="emsr_curve"),
        t.overbooking_png(100, 0.12, 400, 120),
        t.price_png(DemandModelInput(model="linear", intercept=100, slope=2), 10),
        t.newsvendor_png(10, 4, 100, 30),
        t.revenue_opportunity_png([1000, 800, 600, 200], [25, 30, 20, 50], 100,
                                  [100, 70, 45, 32]),
        t.bid_price_png([ProductInput(fare=200, uses={"R": 1}, demand=60),
                         ProductInput(fare=100, uses={"R": 1}, demand=80)], {"R": 100}),
    ]
    for png in pngs:
        assert isinstance(png, bytes)
        assert png[:4] == b"\x89PNG"
