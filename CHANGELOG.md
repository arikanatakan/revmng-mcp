# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project uses
[semantic versioning](https://semver.org/).

## [0.1.0] - 2026-06-17

First release.

### Added

- Analysis tools wrapping revmng: `protection_levels` (EMSR-b, EMSR-a or the
  exact optimal DP), `overbooking_limit`, `newsvendor`, `optimal_price`,
  `revenue_opportunity`, `evaluate_group`, `evaluate_stay`, `bid_prices`,
  `metrics` and `describe_inputs`.
- Chart tools returning PNG images: `protection_chart` (booking limits or EMSR
  curves), `overbooking_chart`, `price_chart`, `newsvendor_chart`,
  `revenue_opportunity_chart` and `bid_price_chart`.
- stdio server built on FastMCP, with read-only tool annotations.
