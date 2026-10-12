# GreenMiles

GreenMiles is an early-stage, nature-first running route recommendation project. Its goal is to help runners find routes that fit their available time while giving priority to greener surroundings. The repository is currently a Phase 0 foundation; route recommendations are not implemented yet.

## Problem

Runners often have a limited window for a run and may prefer a route with more trees, parks, or other green spaces over the most direct path. GreenMiles aims to bring those needs together: a route should suit the runner's available time and favor a more nature-oriented experience.

## Current status

Phase 0 currently provides application configuration, `.env` environment-variable support, console and rotating file logging, Pydantic validation, and basic tests for configuration and logging. Routing settings exist as configuration values only. There is no route generation, map interface, AI feature, or KML export in the current code.

## Roadmap

Planned work, subject to design and contributor interest:

1. Ingest geographic data, beginning with OpenStreetMap.
2. Define analytical data models and add data-quality checks.
3. Generate and rank routes using runner constraints and nature-oriented criteria.
4. Export generated routes as KML.
5. Optionally provide local, open-weight AI-generated explanations for route recommendations.
6. Build a web interface for using the recommendations.

These are future goals, not available features. Technologies for them have not been selected unless noted above.

## Tech stack

**Current implementation:** Python 3.14+, `uv` for environment and dependency management, Pydantic for configuration validation, python-dotenv for loading local environment variables, and Loguru for logging. Development dependencies are pytest and Ruff; the project is built with `uv_build`.

**Planned:** OpenStreetMap as a geographic data source, with the route, KML, optional local AI, and web technologies to be determined as those phases are designed.

## Prerequisites

- Python 3.14 or newer (the repository's `.python-version` selects 3.14).
- [uv](https://docs.astral.sh/uv/) installed and available on your `PATH`.
- Git.

## Local setup

Clone the repository and install the project with its development dependency group:

```sh
git clone https://github.com/krish007code/greenmiles.git
cd greenmiles
uv sync --dev
```

`uv sync --dev` reads `pyproject.toml` and `uv.lock`, creates or updates the project environment, installs the project, and includes the `dev` group. The project defines a `greenmiles` console-script entry point, but the current `main()` only prints a greeting; it does not run route recommendations.

## Configuration

The defaults are in `config/app.ini`. Configuration is loaded by `greenmiles.config.load_config()`, validated with Pydantic, and can be overridden by the following environment variables:

| Variable | Overrides | Default |
| --- | --- | --- |
| `GREENMILES_ENV` | `[application] environment` | `development` |
| `GREENMILES_LOG_LEVEL` | `[logging] level` | `INFO` |

Copy `.env.example` to `.env` in the repository root to set these local values; `.env` is ignored by Git. The application loads that file when configuration is imported. Do not commit secrets. The `[routing]` values (`default_pace_min_per_km` and `max_candidates`) are validated configuration placeholders; there are no environment-variable overrides for them and no routing behavior yet.

Logging writes to the configured directory (currently `utility/logs`) and to standard error. The file logger rotates at 10 MB, retains logs for 10 days, and compresses rotated files.

## Tests and quality checks

Run from the repository root after `uv sync --dev`:

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The final command checks formatting without modifying files.

## Project structure

| Path | Purpose |
| --- | --- |
| `src/greenmiles/` | Installable Python package and application entry point. |
| `src/greenmiles/config.py` | INI loading, environment overrides, and validated configuration models. |
| `src/greenmiles/utility/custom_logger.py` | Console and rotating file logger setup. |
| `tests/` | Configuration and logger tests. |
| `config/app.ini` | Application, logging, and placeholder routing defaults. |
| `.env.example` | Example local environment overrides; copy to `.env` to use. |
| `data/raw/`, `data/processed/`, `data/sample/` | Directories reserved for raw, processed, and sample data as data work is added. |
| `utility/logs/` | Default location for generated log files. |
| `pyproject.toml`, `uv.lock` | Project metadata, dependency groups, and locked dependency versions. |
| `.python-version` | Selects Python 3.14 for compatible tools. |
| `docs/` | Project documentation area. |

## Data sources and attribution

OpenStreetMap is a **planned** data source and is not integrated yet. When OSM data is added, the implementation and any distribution of derived data must follow the [OpenStreetMap copyright and license requirements](https://www.openstreetmap.org/copyright), including appropriate attribution (for example, “© OpenStreetMap contributors”) and applicable Open Database License (ODbL) obligations. Review the OSM terms for the specific data use and outputs before release.

## Contributing

Small, focused contributions are welcome. Please include or update tests for behavior changes, document configuration or workflow changes, and run the test and Ruff checks above before opening a pull request. For larger roadmap items, discuss the design and scope before implementation.

## License

No license is confirmed in the repository. Confirm the intended license and add the appropriate license file before presenting GreenMiles as an openly licensed project.
