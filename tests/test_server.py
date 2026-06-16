def test_server_imports_and_wires():
    from revmng_mcp import server

    assert server.mcp is not None
    assert callable(server.main)


def test_all_tools_registered():
    import asyncio

    from revmng_mcp import server

    names = {tool.name for tool in asyncio.run(server.mcp.list_tools())}
    expected = {
        "protection_levels", "overbooking_limit", "newsvendor", "optimal_price",
        "revenue_opportunity", "evaluate_group", "evaluate_stay", "bid_prices",
        "metrics", "describe_inputs",
        "protection_chart", "overbooking_chart", "price_chart", "newsvendor_chart",
        "revenue_opportunity_chart", "bid_price_chart",
    }
    assert expected <= names
