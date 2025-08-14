"""Chart generation module for Zscaler ticket data."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from zn_report.config import Style

# Seed for deterministic plot generation
np.random.seed(42)

logger = logging.getLogger(__name__)


def _apply_common_styles(
    fig: plt.Figure,
    ax: plt.Axes,
    style: Style,
    title: str,
    xlabel: str = "",
    ylabel: str = "",
) -> None:
    """Apply common styling to a Matplotlib figure and axes."""
    fig.set_dpi(144)
    fig.patch.set_facecolor("white")

    plt.rcParams["font.family"] = style.font_family

    ax.set_title(title.upper(), fontsize=12, weight="bold", color=style.palette.primary)
    ax.set_xlabel(xlabel, fontsize=9, color=style.palette.muted)
    ax.set_ylabel(ylabel, fontsize=9, color=style.palette.muted)

    ax.grid(axis="y", linestyle="--", color=style.palette.muted, alpha=0.5)
    ax.tick_params(axis="both", which="major", labelsize=8, labelcolor=style.palette.secondary)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(style.palette.muted)
    ax.spines["bottom"].set_color(style.palette.muted)


def _plot_resolved_per_day(data: list[dict[str, Any]], ax: plt.Axes, style: Style) -> None:
    """C1: Plot resolved tickets per day as a bar chart."""
    if not data:
        return
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    ax.bar(df["date"], df["count"], color=style.palette.primary)
    ax.figure.autofmt_xdate()


def _plot_opened_vs_resolved(data: dict[str, list], ax: plt.Axes, style: Style) -> None:
    """C2: Plot opened vs. resolved tickets as a line chart."""
    if not data or not data.get("dates"):
        return
    dates = pd.to_datetime(data["dates"])
    ax.plot(dates, data["opened"], label="Opened", color=style.palette.accent)
    ax.plot(dates, data["resolved"], label="Resolved", color=style.palette.primary)
    ax.legend()
    ax.figure.autofmt_xdate()


def _plot_open_by_state(data: dict[str, int], ax: plt.Axes, style: Style) -> None:
    """C3: Plot open tickets by state as a pie chart."""
    if not data or sum(data.values()) == 0:
        ax.text(0.5, 0.5, "No Open Tickets", ha="center", va="center")
        ax.set_axis_off()
        return

    # Fixed order for deterministic color mapping
    states = ["New", "In Progress", "On Hold"]
    counts = [data.get(s, 0) for s in states]
    # Cycle through categorical colors to avoid index errors if palette is small
    colors = [
        style.palette.categorical[i % len(style.palette.categorical)]
        for i in range(len(states))
    ]

    # Filter out states with zero count to avoid cluttering the pie chart
    eff_items = [
        (state, count, color)
        for state, count, color in zip(states, counts, colors)
        if count > 0
    ]
    eff_labels, eff_counts, eff_colors = zip(*eff_items) if eff_items else ([], [], [])

    ax.pie(
        eff_counts,
        labels=eff_labels,
        colors=eff_colors,
        autopct="%1.1f%%",
        startangle=90,
        textprops={"color": style.palette.secondary},
    )
    ax.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.


def _plot_resolved_by_assignee(data: list[dict[str, Any]], ax: plt.Axes, style: Style) -> None:
    """C4: Plot top 10 resolved by assignee as a horizontal bar chart."""
    if not data:
        return
    df = pd.DataFrame(data)
    # Data is pre-sorted desc; reverse for plotting (top item at the top)
    df = df.iloc[::-1]
    ax.barh(df["assignee"], df["count"], color=style.palette.primary)


def _plot_top_5_tags(data: list[dict[str, Any]], ax: plt.Axes, style: Style) -> None:
    """C5: Plot top 5 tags as a horizontal bar chart."""
    if not data:
        return
    df = pd.DataFrame(data)
    # Data is pre-sorted desc; reverse for plotting (top item at the top)
    df = df.iloc[::-1]
    ax.barh(df["tag"], df["count"], color=style.palette.accent)


def render_charts(metrics: dict, style: Style, out_dir: Path) -> dict[str, Path]:
    """
    Orchestrates the creation of all charts.

    Args:
        metrics: The metrics dictionary (UPT v3 format).
        style: The style configuration object.
        out_dir: The directory to save the chart PNG files.

    Returns:
        A dictionary mapping chart IDs to the Path of the generated PNG file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_paths = {}

    chart_definitions = {
        "resolved_per_day": {
            "func": _plot_resolved_per_day,
            "data": metrics.get("series", {}).get("resolved_per_day", []),
            "title": "Resolved Tickets per Day",
            "xlabel": "Date",
            "ylabel": "Tickets",
        },
        "opened_vs_resolved": {
            "func": _plot_opened_vs_resolved,
            "data": metrics.get("series", {}).get("opened_vs_resolved", {}),
            "title": "Opened vs. Resolved Tickets",
            "xlabel": "Date",
            "ylabel": "Tickets",
        },
        "open_by_state": {
            "func": _plot_open_by_state,
            "data": metrics.get("kpis", {}).get("open_by_state", {}),
            "title": "Open Tickets by State",
        },
        "resolved_by_assignee": {
            "func": _plot_resolved_by_assignee,
            "data": metrics.get("tables", {}).get("resolved_by_assignee", []),
            "title": "Top 10 Resolved by Assignee",
            "xlabel": "Tickets Resolved",
        },
        "top_5_tags": {
            "func": _plot_top_5_tags,
            "data": metrics.get("tables", {}).get("top_5_tags", []),
            "title": "Top 5 Tags",
            "xlabel": "Count",
        },
    }

    for chart_id, definition in chart_definitions.items():
        logger.info(f"Generating chart: {chart_id}")
        fig, ax = plt.subplots(figsize=(6, 4))
        filepath = out_dir / f"{chart_id}.png"

        try:
            # Call the specific plot function
            definition["func"](definition["data"], ax, style)

            # Apply common styles
            _apply_common_styles(
                fig,
                ax,
                style,
                title=definition["title"],
                xlabel=definition.get("xlabel", ""),
                ylabel=definition.get("ylabel", ""),
            )

            # Save the figure
            plt.tight_layout()
            fig.savefig(filepath, bbox_inches="tight")
            logger.info(f"Saved chart to {filepath}")

        except Exception as e:
            logger.error(f"Failed to generate chart {chart_id}: {e}", exc_info=True)
            # In case of error, create a placeholder image with error text
            ax.cla()  # Clear axis to remove any partially drawn plots
            ax.text(0.5, 0.5, f"Error generating chart:\n{e}", ha="center", va="center", color="red")
            ax.set_axis_off()  # Hide axes for a cleaner error image
            fig.savefig(filepath)

        finally:
            chart_paths[chart_id] = filepath
            plt.close(fig)

    return chart_paths
