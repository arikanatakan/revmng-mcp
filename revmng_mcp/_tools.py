"""Tool logic, kept free of the MCP SDK so it can be tested directly.

Each analysis tool calls the revmng library and returns its JSON-safe payload
(the decision, provenance) plus a plain-language summary. Chart helpers render a
PNG. The arithmetic lives entirely in revmng; this module only adapts inputs and
shapes the output.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")

import revmng  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

NOTES = (
    "All fares, costs and revenue are in the same currency; times and demand in "
    "consistent units. Demand for the capacity-control methods is assumed normal "
    "and independent, with low-before-high arrival. The tools compute decisions "
    "from the demand you supply; forecasting demand is out of scope."
)

DEFINITIONS = [
    "Littlewood (two classes): protect y = mu + z*sigma seats for the high fare, "
    "with z = Phi^-1(1 - fare_low / fare_high)",
    "EMSR-b / EMSR-a: heuristics for nested protection levels with more than two "
    "classes; for two classes EMSR-b equals Littlewood's optimal rule",
    "Optimal (DP): the exact optimal nested protection levels for the static "
    "single-resource model, with the optimal expected revenue",
    "Overbooking: authorize capacity / (1 - no_show_rate) at the service level, "
    "or the cost-minimising limit given denied-boarding and spoilage costs",
    "Newsvendor: the order quantity at the critical fractile "
    "(price - cost) / ((price - cost) + (cost - salvage))",
    "Optimal price: the profit-maximising price for a linear or "
    "constant-elasticity demand curve (Lerner)",
    "Revenue opportunity (ROM): (realized - no-control) / (perfect - no-control) "
    "for a set of nested booking limits",
    "Group displacement: accept a group when its contribution covers the lost "
    "contribution of the demand it displaces",
    "Length-of-stay: accept a multi-night stay when its total rate covers the sum "
    "of the nightly bid prices",
    "Network bid price: the shadow price of each resource from the deterministic "
    "LP; accept a product when its fare covers the bid prices it uses",
    "Metrics: RevPAR = room revenue / available rooms; ADR = room revenue / rooms "
    "sold; occupancy = rooms sold / available rooms; yield = passenger revenue / "
    "RPM; load factor = traffic / capacity",
]


# --------------------------------------------------------------------------- #
# Input models
# --------------------------------------------------------------------------- #
class FareClassInput(BaseModel):
    """One fare class: its fare and its (normal) demand mean and std dev."""

    fare: float = Field(description="Fare for this class (highest to lowest).")
    mean: float = Field(description="Mean demand for this class.")
    sd: float = Field(default=0.0, description="Standard deviation of demand.")
    name: str | None = Field(default=None, description="Optional class label.")


class DemandModelInput(BaseModel):
    """A demand curve: linear q = intercept - slope*p, or constant elasticity."""

    model: str = Field(default="linear",
                       description="'linear' or 'constant_elasticity'.")
    intercept: float | None = Field(default=None, description="Linear demand intercept a.")
    slope: float | None = Field(default=None, description="Linear demand slope b (> 0).")
    scale: float | None = Field(default=None, description="Constant-elasticity scale a.")
    elasticity: float | None = Field(
        default=None, description="Constant-elasticity exponent (> 1).")


class ProductInput(BaseModel):
    """A network product: its fare, the resources it uses, and its demand."""

    fare: float = Field(description="Revenue from selling this product.")
    uses: dict[str, float] = Field(description="Resource -> units consumed.")
    demand: float = Field(description="Expected demand (upper bound) for this product.")
    name: str | None = Field(default=None, description="Optional product label.")


class MetricsInput(BaseModel):
    """Inputs for the performance ratios; give the ones you have."""

    room_revenue: float | None = Field(default=None, description="Room revenue.")
    rooms_sold: float | None = Field(default=None, description="Rooms sold.")
    available_rooms: float | None = Field(default=None, description="Available rooms.")
    passenger_revenue: float | None = Field(default=None, description="Passenger revenue.")
    revenue_passenger_units: float | None = Field(
        default=None, description="Revenue passenger miles or kilometres.")
    traffic: float | None = Field(default=None, description="Traffic (e.g. RPK, or seats sold).")
    capacity: float | None = Field(default=None, description="Capacity (e.g. ASK, or seats).")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _payload(result) -> dict:
    out = result.to_dict()
    out["summary"] = result.summary()
    return out


def _classes(classes: list[FareClassInput]) -> list[dict]:
    return [c.model_dump(exclude_none=True) for c in classes]


def _allocation(classes: list[FareClassInput], capacity: float, method: str):
    cls = _classes(classes)
    if method == "emsr_b":
        return revmng.emsr_b(cls, capacity)
    if method == "emsr_a":
        return revmng.emsr_a(cls, capacity)
    if method == "optimal":
        return revmng.optimal_protection_levels(cls, capacity)
    raise ValueError("method must be 'emsr_b', 'emsr_a' or 'optimal'")


def _demand_model(demand: DemandModelInput):
    if demand.model == "linear":
        if demand.intercept is None or demand.slope is None:
            raise ValueError("linear demand needs intercept and slope")
        return revmng.LinearDemand(demand.intercept, demand.slope)
    if demand.model == "constant_elasticity":
        if demand.scale is None or demand.elasticity is None:
            raise ValueError("constant_elasticity demand needs scale and elasticity")
        return revmng.ConstantElasticityDemand(demand.scale, demand.elasticity)
    raise ValueError("model must be 'linear' or 'constant_elasticity'")


def _png(fig) -> bytes:
    import matplotlib.pyplot as plt

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


_HINT = "call describe_inputs for the fields and methods"


# --------------------------------------------------------------------------- #
# Analysis tools
# --------------------------------------------------------------------------- #
def protection_levels(classes: list[FareClassInput], capacity: float,
                      method: str = "emsr_b") -> dict:
    """Nested protection levels and booking limits for one resource.

    ``method`` is 'emsr_b' (the industry-standard heuristic), 'emsr_a' (more
    conservative) or 'optimal' (the exact dynamic program, which also returns the
    optimal expected revenue). Two classes under EMSR-b equal Littlewood's rule.
    """
    try:
        return _payload(_allocation(classes, capacity, method))
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def overbooking_limit(capacity: int, no_show_rate: float,
                      denied_cost: float | None = None,
                      spoilage_cost: float | None = None) -> dict:
    """Overbooking authorization limit for one resource.

    With both ``denied_cost`` (per bumped customer) and ``spoilage_cost`` (per
    empty seat) the cost-minimising limit is returned; otherwise the
    service-level limit ``round(capacity / (1 - no_show_rate))``.
    """
    try:
        return _payload(revmng.overbooking_limit(
            capacity, no_show_rate=no_show_rate, denied_cost=denied_cost,
            spoilage_cost=spoilage_cost))
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def newsvendor(price: float, cost: float, demand_mean: float, demand_sd: float,
               salvage: float = 0.0) -> dict:
    """Optimal single-period stocking quantity (the critical-fractile rule)."""
    try:
        return _payload(revmng.newsvendor(price, cost, demand_mean, demand_sd,
                                          salvage=salvage))
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def optimal_price(demand: DemandModelInput, unit_cost: float = 0.0) -> dict:
    """Profit-maximising price for a linear or constant-elasticity demand curve."""
    try:
        return _payload(revmng.optimal_price(_demand_model(demand), unit_cost))
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def revenue_opportunity(fares: list[float], demand: list[float], capacity: float,
                        booking_limits: list[float] | None = None) -> dict:
    """Score booking limits against perfect-hindsight and no-control benchmarks.

    Returns perfect, no-control and (with ``booking_limits``) realised revenue and
    the revenue opportunity metric (ROM).
    """
    try:
        return _payload(revmng.revenue_opportunity(
            fares, demand, capacity, booking_limits=booking_limits))
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def evaluate_group(group_rate: float, units: float, variable_cost: float = 0.0,
                   displacement_cost: float | None = None,
                   marginal_value: float | None = None,
                   group_size: float | None = None, capacity: float | None = None,
                   demand: list[float] | None = None,
                   value_per_unit: float | None = None) -> dict:
    """Accept or reject a group by displacement analysis.

    Give the total ``displacement_cost``, or a per-unit ``marginal_value``, or the
    scenario (``group_size``, ``capacity``, per-period ``demand`` and
    ``value_per_unit``) from which the displacement is computed.
    """
    try:
        if displacement_cost is None and marginal_value is None:
            if None in (group_size, capacity, demand, value_per_unit):
                return {"error": "give displacement_cost, marginal_value, or the "
                        "scenario (group_size, capacity, demand, value_per_unit)",
                        "hint": _HINT}
            displacement_cost = revmng.group_displacement(
                group_size, capacity, demand, value_per_unit)
        return _payload(revmng.evaluate_group(
            group_rate, units, displacement_cost=displacement_cost,
            marginal_value=marginal_value, variable_cost=variable_cost))
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def evaluate_stay(nightly_bid_prices: dict[str, float], nights: list[str],
                  total_rate: float) -> dict:
    """Accept or reject a multi-night stay against the nightly bid prices."""
    try:
        return _payload(revmng.evaluate_stay(nightly_bid_prices, nights, total_rate))
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def bid_prices(products: list[ProductInput], capacities: dict[str, float]) -> dict:
    """Network bid prices and the deterministic-LP allocation across resources."""
    try:
        prods = [p.model_dump(exclude_none=True) for p in products]
        return _payload(revmng.bid_prices(prods, capacities))
    except (ValueError, TypeError, ImportError) as exc:
        return {"error": str(exc), "hint": _HINT}


def metrics(inputs: MetricsInput) -> dict:
    """The standard performance ratios from whichever inputs are provided."""
    out: dict = {}
    try:
        i = inputs
        if i.room_revenue is not None and i.available_rooms is not None:
            out["revpar"] = revmng.revpar(i.room_revenue, i.available_rooms)
        if i.room_revenue is not None and i.rooms_sold is not None:
            out["adr"] = revmng.adr(i.room_revenue, i.rooms_sold)
        if i.rooms_sold is not None and i.available_rooms is not None:
            out["occupancy"] = revmng.occupancy(i.rooms_sold, i.available_rooms)
        if i.passenger_revenue is not None and i.revenue_passenger_units is not None:
            out["yield"] = revmng.yield_(i.passenger_revenue, i.revenue_passenger_units)
        if i.traffic is not None and i.capacity is not None:
            out["load_factor"] = revmng.load_factor(i.traffic, i.capacity)
        if not out:
            return {"error": "give inputs for at least one metric", "hint": _HINT}
        return {"metrics": out}
    except (ValueError, TypeError) as exc:
        return {"error": str(exc), "hint": _HINT}


def describe_inputs() -> dict:
    """The input fields, the method definitions and the modelling notes."""
    return {
        "notes": NOTES,
        "fare_class_fields": {n: f.description
                              for n, f in FareClassInput.model_fields.items()},
        "definitions": DEFINITIONS,
        "methods": ["protection_levels (emsr_b / emsr_a / optimal)",
                    "overbooking_limit", "newsvendor", "optimal_price",
                    "revenue_opportunity", "evaluate_group", "evaluate_stay",
                    "bid_prices", "metrics"],
    }


# --------------------------------------------------------------------------- #
# Chart helpers (return PNG bytes)
# --------------------------------------------------------------------------- #
def protection_png(classes: list[FareClassInput], capacity: float,
                   method: str = "emsr_b", kind: str = "booking_limits") -> bytes:
    result = _allocation(classes, capacity, method)
    if kind == "emsr_curve":
        return _png(revmng.emsr_curve(result))
    return _png(revmng.booking_limit_chart(result))


def overbooking_png(capacity: int, no_show_rate: float, denied_cost: float,
                    spoilage_cost: float) -> bytes:
    return _png(revmng.overbooking_cost_curve(
        capacity, no_show_rate, denied_cost=denied_cost, spoilage_cost=spoilage_cost))


def price_png(demand: DemandModelInput, unit_cost: float = 0.0) -> bytes:
    return _png(revmng.price_curve(_demand_model(demand), unit_cost))


def newsvendor_png(price: float, cost: float, demand_mean: float, demand_sd: float,
                   salvage: float = 0.0) -> bytes:
    return _png(revmng.newsvendor_curve(price, cost, demand_mean, demand_sd,
                                        salvage=salvage))


def revenue_opportunity_png(fares: list[float], demand: list[float], capacity: float,
                            booking_limits: list[float] | None = None) -> bytes:
    result = revmng.revenue_opportunity(fares, demand, capacity,
                                        booking_limits=booking_limits)
    return _png(revmng.revenue_opportunity_chart(result))


def bid_price_png(products: list[ProductInput], capacities: dict[str, float]) -> bytes:
    prods = [p.model_dump(exclude_none=True) for p in products]
    return _png(revmng.bid_price_chart(revmng.bid_prices(prods, capacities)))
