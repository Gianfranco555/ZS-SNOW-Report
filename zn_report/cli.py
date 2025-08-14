"""Command-line interface for the Zscaler ServiceNow Incident Reporter."""

import argparse
import logging
import sys
import tempfile
import importlib.resources
from datetime import datetime
from pathlib import Path

import yaml

from zn_report import charts, io_loader, metrics, report, time_ops
from zn_report.config import load_config
from zn_report.exceptions import (
    AllRowsDroppedError,
    CLIError,
    FileIOError,
    InvalidArgumentsError,
    MissingHeadersError,
    ReportRenderError,
)

# Setup logger
logger = logging.getLogger(__name__)


def _parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a Zscaler ServiceNow incident report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # ... (argument definitions are unchanged)
    parser.add_argument(
        "--csv", required=True, help="Path to the input ServiceNow CSV export."
    )
    parser.add_argument(
        "--start", required=True, help="The report start date (YYYY-MM-DD)."
    )
    parser.add_argument(
        "--end", required=True, help="The report end date (YYYY-MM-DD)."
    )
    parser.add_argument(
        "--out", default="./report.pdf", help="Path to the output report file."
    )
    parser.add_argument(
        "--fmt", default="pdf", choices=["pdf", "docx"], help="The output format."
    )
    parser.add_argument(
        "--tz", default="UTC", help="The display timezone for the report."
    )
    parser.add_argument(
        "--config", type=Path, help="Path to a custom settings.yaml file."
    )
    parser.add_argument(
        "--title", help="The main title of the report. Overrides config file."
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["INFO", "DEBUG"],
        help="Set the logging level.",
    )
    parser.add_argument(
        "--chunksize", type=int, help="Process the CSV in chunks of this size."
    )
    parser.add_argument(
        "--ai-summarizer",
        default="none",
        choices=["none", "local", "openai"],
        help="The AI summarizer to use.",
    )
    parser.add_argument(
        "--summary-max-chars",
        type=int,
        default=700,
        help="The maximum character length for the summary.",
    )
    return parser.parse_args()


def setup_logging(level: str):
    """Configure logging."""
    logging.basicConfig(
        level=level, format="%(levelname)-5s %(message)s", stream=sys.stdout
    )


def run_report_workflow(args):
    """Orchestrate the report generation workflow, raising exceptions on failure."""
    # 1. Configuration
    settings = None
    if args.config:
        try:
            with args.config.open() as f:
                settings = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileIOError(f"Config file not found at '{args.config}'")
        except (yaml.YAMLError, TypeError) as e:
            raise InvalidArgumentsError(f"Error parsing YAML config: {e}")

    cfg = load_config(settings)
    if args.title:
        cfg.title = args.title

    # 2. Data Loading
    try:
        df = io_loader.load_csv(args.csv, chunksize=args.chunksize)
    except FileNotFoundError:
        raise FileIOError(f"CSV file not found at '{args.csv}'")
    except MissingHeadersError as e:
        # Re-raise as InvalidArgumentsError to be caught by the handler in cli_main
        raise InvalidArgumentsError(str(e)) from e

    logger.info(f"Loaded {len(df)} rows; tz={args.tz}")

    # 3. Time Operations
    start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    df = time_ops.parse_dates(df, tz=args.tz)
    if df["opened_at"].isna().all():
        raise AllRowsDroppedError()

    # 4. Metrics Computation
    computed_metrics = metrics.compute_metrics(df, start_date, end_date, tz=args.tz)
    dropped = computed_metrics["metadata"]["dropped"]
    logger.info(
        f"Dropped: invalid_opened={dropped['opened_at']}, invalid_resolved={dropped['resolved_at']}, both={dropped['both']}"
    )
    for warning in computed_metrics["metadata"]["warnings"]:
        logger.warning(
            warning.replace(
                "Reports based on an updated-date window may undercount newly opened tickets.",
                "Opened-per-day may be incomplete (updated-window export)",
            )
        )
    kpis = computed_metrics["kpis"]
    logger.info(
        f"Metrics: resolved={kpis['resolved_count']}; avg/day={kpis['resolved_per_day_avg']:.2f}; avg TTR={kpis['avg_ttr_hours']}h; open(total)={kpis['total_open_tickets']}"
    )

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # 5. Chart Rendering
        rendered_charts = charts.render_charts(
            metrics=computed_metrics, style=cfg.style, out_dir=temp_dir
        )

        # 6. Report Assembly
        try:
            template_ref = importlib.resources.files("zn_report").joinpath(
                "templates", "report.html.j2"
            )
            with importlib.resources.as_file(template_ref) as template_path:
                report.assemble_report(
                    metrics=computed_metrics,
                    chart_paths=rendered_charts,
                    config=cfg,
                    template_path=template_path,
                    output_path=Path(args.out),
                )
        except Exception as e:
            raise ReportRenderError(
                f"Error during report rendering/assembly: {e}"
            ) from e

    logger.info(f"Report written to {args.out}")


def cli_main():
    """CLI entrypoint for the Zscaler ServiceNow Incident Reporter."""
    args = _parse_args()
    setup_logging(args.log_level)

    try:
        # --- Argument Validation ---
        try:
            start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
            end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
            if start_date > end_date:
                raise InvalidArgumentsError(
                    f"Start date ({args.start}) cannot be after end date ({args.end})."
                )
        except ValueError:
            raise InvalidArgumentsError("Invalid date format. Please use YYYY-MM-DD.")

        # --- Run Core Workflow ---
        run_report_workflow(args)

    except CLIError as e:
        logger.error(f"Error: {e.message}")
        sys.exit(e.exit_code)
    except Exception as e:
        logger.error(
            f"An unexpected critical error occurred: {e}",
            exc_info=args.log_level == "DEBUG",
        )
        sys.exit(1)  # Generic catch-all for truly unexpected errors

    sys.exit(0)


if __name__ == "__main__":
    cli_main()
