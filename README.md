# GreenMiles

GreenMiles is an early-stage, nature-first running route recommendation project. Its goal is to help runners find routes that fit their available time while giving priority to greener surroundings. Phase 1 provides an offline-first OpenStreetMap (OSM) JSON ingestion and GeoJSON normalization pipeline; route recommendations are not implemented yet.

## Problem

Runners often have a limited window for a run and may prefer a route with more trees, parks, or other green spaces over the most direct path. GreenMiles aims to bring those needs together: a route should suit the runner's available time and favor a more nature-oriented experience.

## Current status

The project provides application configuration, `.env` environment-variable support, console and rotating file logging, Pydantic validation, and an offline-first OSM JSON-to-GeoJSON pipeline with tests. Routing settings exist as configuration values only. There is no route generation, map interface, AI feature, or KML export in the current code.

## Roadmap

Planned work, subject to design and contributor interest:

1. Extend geographic data ingestion beyond saved OSM exports.
2. Define analytical data models and add data-quality checks.
3. Generate and rank routes using runner constraints and nature-oriented criteria.
4. Export generated routes as KML.
5. Optionally provide local, open-weight AI-generated explanations for route recommendations.
6. Build a web interface for using the recommendations.

These are future goals, not available features. Technologies for them have not been selected unless noted above.

## Tech stack

**Current implementation:** Python 3.14+, `uv` for environment and dependency management, Pydantic for configuration validation, python-dotenv for loading local environment variables, and Loguru for logging. The OSM ingestion uses the Python standard library for JSON parsing, coordinate validation, and GeoJSON serialization; it adds no geospatial runtime dependency. Development dependencies are pytest and Ruff; the project is built with `uv_build`.

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

`uv sync --dev` reads `pyproject.toml` and `uv.lock`, creates or updates the project environment, installs the project, and includes the `dev` group. The project defines a `greenmiles` console-script entry point, but route recommendations are not implemented. Run local OSM ingestion with the module command below.

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

## Offline OSM ingestion (Phase 1)

The pipeline reads an existing Overpass/OSM JSON export from disk and does not
make network requests. The saved input fixture is
`data/raw/osm/sample_manesar.json`; it contains 42 OSM ways (41 tagged with
`highway` and one tagged `leisure=park`). The importer itself does not download
this file. If you replace it with a different real export, keep that raw file
under `data/raw/osm/` and run:

```sh
uv run python -m greenmiles.ingest_osm
```

To select different paths, pass `--input path/to/export.json` and
`--output path/to/output.geojson`. The defaults write
`data/processed/osm/sample_manesar.geojson` and its companion
`data/processed/osm/sample_manesar.metadata.json`. Processed outputs are locally
generated and ignored by Git. A valid input with no elements produces an empty
FeatureCollection and `processing_outcome: "empty"`; unsupported or incomplete
geometries are listed in metadata and produce a `partial` outcome rather than
being assigned invented coordinates. Duplicate elements are identified by
`(OSM type, OSM ID)`; the first copy is retained.

Feature categories are determined solely from OSM tags: `highway=footway`,
`path`, or `pedestrian` maps to `pedestrian_path`; `highway=residential`,
`service`, `living_street`, or `unclassified` maps to `road`; any other
`highway` value maps to `other_highway`; and features tagged with `leisure`,
`landuse`, or `natural` are categorized as `green_space` when no highway
category applies. When a highway feature also has a green-space tag, its
category is suffixed with `_and_green_space` (for example,
`pedestrian_path_and_green_space`). These labels describe source tags only;
they do not establish public access, pedestrian access, or running suitability.

Coordinates are serialized in GeoJSON longitude/latitude order and remain in
WGS84 (EPSG:4326); no projection is performed. Ways with valid coordinate
arrays become LineStrings, except closed green-space rings, which become
Polygons. OSM nodes with `lat`/`lon` become Points. Relation geometry is handled
when supplied as a direct coordinate array; member-assembled/multipolygon
relation structures are not assembled in this phase and are reported as
unsupported geometry.

The library boundary accepts decoded OSM documents independently of the local
file reader, allowing a future Overpass adapter to feed the same normalization
without putting network behavior in the offline pipeline or tests. No live
Overpass client is included.

## Project structure

| Path | Purpose |
| --- | --- |
| `src/greenmiles/` | Installable Python package and application entry point. |
| `src/greenmiles/config.py` | INI loading, environment overrides, and validated configuration models. |
| `src/greenmiles/ingest_osm.py` | Offline OSM JSON reader, shared normalization, GeoJSON output, metadata, and module entry point. |
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

The real test fixture at `data/raw/osm/sample_manesar.json` contains OpenStreetMap
data from an Overpass export. Its embedded metadata retains the Overpass generator,
OSM base timestamp, and upstream ODbL notice. Attribute the data to “© OpenStreetMap
contributors” and follow the [OpenStreetMap copyright and license requirements](https://www.openstreetmap.org/copyright), including applicable ODbL obligations
when redistributing the fixture or derived databases. This ODbL data notice applies
to the OSM data, not to GreenMiles source code; the repository does not currently
declare a project code license. The ingestion pipeline carries source type, source
filename, retrieval date when present, and attribution/license information into
its outputs. GreenMiles makes no live OSM downloads in this phase.

## Contributing

Small, focused contributions are welcome. Please include or update tests for behavior changes, document configuration or workflow changes, and run the test and Ruff checks above before opening a pull request. For larger roadmap items, discuss the design and scope before implementation.

## License

No license is confirmed in the repository. Confirm the intended license and add the appropriate license file before presenting GreenMiles as an openly licensed project.
