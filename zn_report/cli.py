"""Command-line interface for the Zscaler ServiceNow Incident Reporter."""

import argparse
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from zn_report import charts, io_loader, metrics, report, time_ops
from zn_report.config import Config, load_config
from zn_report.exceptions import MissingHeadersError

# Setup logger
logger = logging.getLogger(__name__)


def _parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate a Zscaler ServiceNow incident report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Required arguments
    parser.add_argument("--csv", required=True, help="Path to the input ServiceNow CSV export.")
    parser.add_argument("--start", required=True, help="The report start date (YYYY-MM-DD).")
    parser.add_argument("--end", required=True, help="The report end date (YYYY-MM-DD).")

    # Optional arguments
    parser.add_argument("--out", default="./report.pdf", help="Path to the output report file.")
    parser.add_argument("--fmt", default="pdf", choices=["pdf", "docx"], help="The output format.")
    parser.add_argument("--tz", default="UTC", help="The display timezone for the report.")
    parser.add_argument("--config", type=Path, help="Path to a custom settings.yaml file.")
    parser.add_argument("--title", help="The main title of the report. Overrides config file.")
    parser.add_argument("--log-level", default="INFO", choices=["INFO", "DEBUG"], help="Set the logging level.")
    parser.add_argument("--chunksize", type=int, help="Process the CSV in chunks of this size.")

    # AI-related arguments (placeholders for now)
    parser.add_argument("--ai-summarizer", default="none", choices=["none", "local", "openai"], help="The AI summarizer to use.")
    parser.add_argument("--summary-max-chars", type=int, default=700, help="The maximum character length for the summary.")

    return parser.parse_args()


def setup_logging(level: str):
    """Configure logging."""
    logging.basicConfig(level=level, format="%(levelname)-5s %(message)s", stream=sys.stdout)


def cli_main():
    """CLI entrypoint for the Zscaler ServiceNow Incident Reporter."""
    args = _parse_args()
    setup_logging(args.log_level)

    # --- Argument Validation ---
    try:
        start_date = datetime.strptime(args.start, "%Y-%m-%d").date()
        end_date = datetime.strptime(args.end, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Error: Invalid date format. Please use YYYY-MM-DD.")
        sys.exit(2)

    if start_date > end_date:
        logger.error(f"Error: Start date ({args.start}) cannot be after end date ({args.end}).")
        sys.exit(2)

    try:
        # 1. Configuration
        settings = None
        if args.config:
            try:
                with args.config.open() as f:
                    settings = yaml.safe_load(f)
            except FileNotFoundError:
                logger.error(f"Error: Config file not found at '{args.config}'")
                sys.exit(5)
            except (yaml.YAMLError, TypeError) as e:
                logger.error(f"Error parsing YAML config: {e}")
                sys.exit(2)

        cfg = load_config(settings)
        if args.title:
            cfg.title = args.title

        # 2. Data Loading
        try:
            df = io_loader.load_csv(args.csv, chunksize=args.chunksize)
        except FileNotFoundError:
            logger.error(f"Error: CSV file not found at '{args.csv}'")
            sys.exit(5)
        except MissingHeadersError as e:
            logger.error(f"Error: Missing required columns in CSV: {e}")
            sys.exit(2)

        logger.info(f"Loaded {len(df)} rows; tz={args.tz}")

        # 3. Time Operations
        df = time_ops.parse_dates(df, tz=args.tz)

        # Check for unusable rows after parsing
        if df["opened_at"].isna().all():
            logger.error("Error: All rows were dropped after date parsing. Cannot generate report.")
            sys.exit(3)

        # 4. Metrics Computation
        computed_metrics = metrics.compute_metrics(df, start_date, end_date, tz=args.tz)

        # Log dropped counts and metrics
        dropped = computed_metrics["metadata"]["dropped"]
        logger.info(f"Dropped: invalid_opened={dropped['opened_at']}, invalid_resolved={dropped['resolved_at']}, both={dropped['both']}")

        for warning in computed_metrics["metadata"]["warnings"]:
             logger.warning(warning.replace("Reports based on an updated-date window may undercount newly opened tickets.", "Opened-per-day may be incomplete (updated-window export)"))

        kpis = computed_metrics["kpis"]
        logger.info(f"Metrics: resolved={kpis['resolved_count']}; avg/day={kpis['resolved_per_day_avg']:.2f}; avg TTR={kpis['avg_ttr_hours']:.2f}h; open(total)={kpis['open_by_state_total']}")

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # 5. Chart Rendering
            rendered_charts = charts.render_charts(
                metrics=computed_metrics,
                style=cfg.style,
                out_dir=temp_dir,
            )

            # 6. Report Assembly
            try:
                template_path = Path(__file__).parent.parent / "templates" / "report.html.j2"
                report.assemble_report(
                    metrics=computed_metrics,
                    chart_paths=rendered_charts,
                    config=cfg,
                    template_path=template_path,
                    output_path=Path(args.out),
                )
            except Exception as e:
                logger.error(f"Error during report rendering/assembly: {e}")
                sys.exit(4)

        logger.info(f"Report written to {args.out}")

    except Exception as e:
        logger.error(f"An unexpected critical error occurred: {e}", exc_info=args.log_level == "DEBUG")
        sys.exit(1) # Generic catch-all

    sys.exit(0)


if __name__ == "__main__":
    cli_main()
