"""Generate the revmng-mcp architecture figure (academic style).

How an AI agent calls the server, which routes to the validated revmng core and
returns a structured result or a chart.
Run:  python assets/architecture.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5})

INK = "#1f2d3d"
MUT = "#5b6b7b"
NEUT_F, NEUT_E = "#eef1f4", "#9aa7b3"
CORE_F, CORE_E = "#dce8f5", "#2c5f8a"
ANA_F, ANA_E = "#eef3f8", "#3b6ea5"
OPT_F, OPT_E = "#e3f1ec", "#3a8f78"
CONT_F, CONT_E = "#f7f9fb", "#c9d2db"
BAN_F, BAN_E = "#f5f7f9", "#cdd6df"
ARROW = "#7c8a99"

fig, ax = plt.subplots(figsize=(11.5, 6.5))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, text, fill, edge, fs=8.4, bold=False, tcol=INK):
    ax.add_patch(FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle="round,pad=0.35,rounding_size=1.4",
        linewidth=1.25, edgecolor=edge, facecolor=fill, zorder=2))
    ax.text(x, y, text, ha="center", va="center", color=tcol, fontsize=fs,
            fontweight="bold" if bold else "normal", zorder=5)


def arrow(x0, y0, x1, y1, color=ARROW, lw=1.2):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=1,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw,
                                shrinkA=1, shrinkB=1))


ax.text(3, 96, "revmng-mcp", fontsize=13.5, fontweight="bold", color=INK, ha="left")
ax.text(3, 91, "validated revenue-management tools for AI agents", fontsize=9.5,
        color=MUT, ha="left", fontstyle="italic")

# agent
box(12, 60, 18, 22, "AI agent\n\nMCP client",
    NEUT_F, NEUT_E, fs=8.2)

# server container
ax.add_patch(FancyBboxPatch((27, 30), 44, 53,
             boxstyle="round,pad=0.4,rounding_size=1.6",
             linewidth=1.4, edgecolor=CONT_E, facecolor=CONT_F, zorder=0))
ax.text(49, 79, "revmng-mcp server  (stdio)", ha="center", fontsize=9.5, color=MUT,
        fontweight="bold")
box(49, 62, 40, 20,
    "Analysis tools  (10)\n"
    "protection_levels · overbooking_limit · newsvendor\n"
    "optimal_price · revenue_opportunity · evaluate_group\n"
    "evaluate_stay · bid_prices · metrics · describe_inputs",
    ANA_F, ANA_E, fs=6.6)
box(49, 43, 40, 13,
    "Chart tools  (6)\n"
    "protection_chart · overbooking_chart · price_chart\n"
    "newsvendor_chart · revenue_opportunity_chart · bid_price_chart",
    OPT_F, OPT_E, fs=6.6)

# core
box(88, 55, 20, 26, "revmng\n\nvalidated\ncomputation\n+ provenance",
    CORE_F, CORE_E, fs=8.6, bold=True)

# forward arrows
arrow(21.2, 60, 26.8, 60)
ax.text(24, 63.5, "call", ha="center", fontsize=7.6, color=MUT)
arrow(69.2, 62, 77.8, 57)
arrow(69.2, 43, 77.8, 53)
ax.text(74, 61, "calls", ha="center", fontsize=7.6, color=MUT)

# return lane
arrow(80, 17, 16, 17, color=OPT_E, lw=1.4)
ax.text(48, 20.5, "results to the agent:  structured JSON "
        "(decision · figures · provenance)   or   PNG chart",
        ha="center", fontsize=7.9, color="#2e7d6b")
arrow(88, 42, 88, 17, color=OPT_E, lw=1.2)
arrow(12, 17, 12, 49, color=OPT_E, lw=1.2)

# banner
box(50, 7.5, 94, 5,
    "the agent interprets   ·   validated code computes   ·   every result "
    "carries provenance",
    BAN_F, BAN_E, fs=8.2, tcol=MUT)

fig.savefig("assets/architecture.png", dpi=200, bbox_inches="tight",
            facecolor="white")
print("wrote assets/architecture.png")
