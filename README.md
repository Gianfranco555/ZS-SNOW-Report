# zn-report

A command-line interface (CLI) tool for generating reports from Zscaler data, designed with an offline-first and deterministic approach. All styling and configuration is handled locally, and the tool uses seeded random number generation to ensure that report generation is repeatable. This guarantees consistent output for the same inputs and configuration, making it a reliable tool for automated reporting workflows.

## Current Features

This repository currently contains the foundational scaffold for the reporting tool, including:

*   **Constants and RNG Seeding**: Core constants and a mechanism for global random number generator (RNG) seeding to ensure deterministic outputs.
*   **Configuration Model**: A robust configuration model using dataclasses for clear and type-safe settings management.
*   **Configuration Loader**: A loader that merges default settings with user-provided configurations from a YAML file.
*   **Example Settings**: An example `settings.example.yaml` to demonstrate how to customize the report.

## Future Development

The following features are planned for future development:

*   **CSV Ingestion**: The ability to ingest data from CSV files.
*   **Metrics Calculation**: The implementation of various metrics calculations based on the ingested data.
*   **Chart Generation**: The creation of charts and visualizations for the report.
*   **PDF/DOCX Export**: The ability to export the final report to PDF and DOCX formats.
*   **CLI Wiring**: The wiring of all components into a user-friendly command-line interface.

## Quickstart

To get started with the `zn-report` tool, you need Python 3.10 or higher.

You can install the package using pip. For development, it is recommended to install it in editable mode:

```bash
pip install -e .
```

Here is a quick example of how to use the library:

```python
from zn_report import apply_global_seed
from zn_report.config import DEFAULT_CONFIG, load_config

# Apply the global seed for deterministic behavior
apply_global_seed()

# Load the default configuration
cfg = load_config()  # uses defaults

# You can also load a custom configuration from a dictionary
# For example, from a loaded YAML file
# custom_settings = {"title": "My Custom Report"}
# cfg = load_config(custom_settings)

print(cfg.title)
```

## CSV Loading (Chunk 2)

```py
from zn_report.io_loader import load_csv
df = load_csv("tickets.csv")         # DataFrame
it = load_csv("tickets.csv", chunksize=100_000)  # Iterator[pd.DataFrame]
```
Note that header failures raise `MissingHeadersError` (later mapped to exit code 2 by the CLI).
