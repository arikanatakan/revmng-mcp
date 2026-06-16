"""The MCP server: registers the revmng tools and runs over stdio.

All tools are pure, read-only computations, marked with annotations so a client
can present and auto-run them safely.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP, Image
from mcp.types import ToolAnnotations

from . import _tools
from ._tools import DemandModelInput, FareClassInput, ProductInput

mcp = FastMCP("revmng")


def _annotations(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=False,
    )


# Analysis tools
mcp.tool(annotations=_annotations("Protection levels and booking limits"))(_tools.protection_levels)
mcp.tool(annotations=_annotations("Overbooking limit"))(_tools.overbooking_limit)
mcp.tool(annotations=_annotations("Newsvendor stocking quantity"))(_tools.newsvendor)
mcp.tool(annotations=_annotations("Profit-maximising price"))(_tools.optimal_price)
mcp.tool(annotations=_annotations("Revenue opportunity (ROM)"))(_tools.revenue_opportunity)
mcp.tool(annotations=_annotations("Evaluate a group (displacement)"))(_tools.evaluate_group)
mcp.tool(annotations=_annotations("Evaluate a length-of-stay request"))(_tools.evaluate_stay)
mcp.tool(annotations=_annotations("Network bid prices"))(_tools.bid_prices)
mcp.tool(annotations=_annotations("Performance metrics"))(_tools.metrics)
mcp.tool(annotations=_annotations("Describe the inputs"))(_tools.describe_inputs)


# Chart tools (return a PNG image)
@mcp.tool(annotations=_annotations("Protection / EMSR chart (PNG)"))
def protection_chart(classes: list[FareClassInput], capacity: float,
                     method: str = "emsr_b", kind: str = "booking_limits") -> Image:
    """Render the nested booking limits, or the EMSR curves with kind='emsr_curve'."""
    return Image(data=_tools.protection_png(classes, capacity, method, kind),
                 format="png")


@mcp.tool(annotations=_annotations("Overbooking cost curve (PNG)"))
def overbooking_chart(capacity: int, no_show_rate: float, denied_cost: float,
                      spoilage_cost: float) -> Image:
    """Render the overbooking cost trade-off against the authorization limit."""
    return Image(data=_tools.overbooking_png(capacity, no_show_rate, denied_cost,
                                             spoilage_cost), format="png")


@mcp.tool(annotations=_annotations("Price optimization chart (PNG)"))
def price_chart(demand: DemandModelInput, unit_cost: float = 0.0) -> Image:
    """Render revenue, profit and demand against price with the optimum marked."""
    return Image(data=_tools.price_png(demand, unit_cost), format="png")


@mcp.tool(annotations=_annotations("Newsvendor profit curve (PNG)"))
def newsvendor_chart(price: float, cost: float, demand_mean: float, demand_sd: float,
                     salvage: float = 0.0) -> Image:
    """Render expected profit against order quantity with the optimum marked."""
    return Image(data=_tools.newsvendor_png(price, cost, demand_mean, demand_sd,
                                            salvage), format="png")


@mcp.tool(annotations=_annotations("Revenue opportunity chart (PNG)"))
def revenue_opportunity_chart(fares: list[float], demand: list[float], capacity: float,
                              booking_limits: list[float] | None = None) -> Image:
    """Render perfect, no-control and realised revenue as a bar chart."""
    return Image(data=_tools.revenue_opportunity_png(fares, demand, capacity,
                                                     booking_limits), format="png")


@mcp.tool(annotations=_annotations("Network bid price chart (PNG)"))
def bid_price_chart(products: list[ProductInput],
                    capacities: dict[str, float]) -> Image:
    """Render the bid price per resource as a bar chart."""
    return Image(data=_tools.bid_price_png(products, capacities), format="png")


def main() -> None:
    """Console-script entry point: run the server on stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
