"""Offline OSM JSON normalization and GeoJSON output."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from loguru import logger

from greenmiles.config import PROJECT_ROOT, load_config
from greenmiles.utility.custom_logger import setup_logger

CRS = "EPSG:4326"
GREEN_TAGS = ("leisure", "landuse", "natural")
# Categories describe OSM tagging only; they do not imply access or suitability.
PEDESTRIAN_HIGHWAYS = frozenset({"footway", "path", "pedestrian"})
ROAD_HIGHWAYS = frozenset({"residential", "service", "living_street", "unclassified"})
RELEVANT_TAGS = (
    "highway",
    "leisure",
    "landuse",
    "natural",
    "access",
    "foot",
    "surface",
)
SUPPORTED_TYPES = {"node", "way", "relation"}


class OSMInputError(ValueError):
    """Raised when an OSM JSON document has an invalid structure."""


class OSMInputSource(Protocol):
    """Boundary for local files now and other OSM providers in the future."""

    source_type: str
    source_filename: str | None

    def read(self) -> Mapping[str, Any]:
        """Return an OSM JSON-like document without changing normalization."""


@dataclass(frozen=True)
class LocalOSMJsonSource:
    """Read a saved Overpass/OSM JSON document without network access."""

    path: Path
    source_type: str = "local_osm_json"

    @property
    def source_filename(self) -> str:
        return self.path.name

    def read(self) -> Mapping[str, Any]:
        if not self.path.is_file():
            raise FileNotFoundError(f"OSM input file not found: {self.path}")

        try:
            with self.path.open(encoding="utf-8") as source_file:
                document = json.load(source_file)
        except json.JSONDecodeError as exc:
            raise OSMInputError(
                f"Malformed JSON in OSM input {self.path}: {exc}"
            ) from exc
        except UnicodeDecodeError as exc:
            raise OSMInputError(f"OSM input is not valid UTF-8: {self.path}") from exc

        return _validate_document(document, self.path)


@dataclass(frozen=True)
class IngestionResult:
    """Locations and summary metadata produced by one processing run."""

    geojson_path: Path
    metadata_path: Path
    metadata: dict[str, Any]


def _validate_document(document: Any, source: Path | None = None) -> Mapping[str, Any]:
    source_label = f" in {source}" if source else ""
    if not isinstance(document, Mapping):
        raise OSMInputError(f"Expected an OSM JSON object{source_label}.")
    elements = document.get("elements")
    if not isinstance(elements, list):
        raise OSMInputError(
            f"Expected the OSM document to contain an 'elements' array{source_label}."
        )
    osm3s = document.get("osm3s", {})
    if osm3s is not None and not isinstance(osm3s, Mapping):
        raise OSMInputError(f"Expected 'osm3s' to be an object{source_label}.")
    return document


def _validate_element(element: Any, index: int) -> tuple[str, int, dict[str, Any]]:
    if not isinstance(element, Mapping):
        raise OSMInputError(f"OSM element at index {index} must be an object.")

    osm_type = element.get("type")
    if osm_type not in SUPPORTED_TYPES:
        raise OSMInputError(
            f"OSM element at index {index} has unsupported type {osm_type!r}; "
            "expected node, way, or relation."
        )
    osm_id = element.get("id")
    if isinstance(osm_id, bool) or not isinstance(osm_id, int) or osm_id < 0:
        raise OSMInputError(
            f"OSM element at index {index} must have a non-negative integer 'id'."
        )

    tags = element.get("tags", {})
    if not isinstance(tags, Mapping) or any(not isinstance(key, str) for key in tags):
        raise OSMInputError(
            f"OSM element {osm_type}/{osm_id} has invalid 'tags'; expected an object "
            "with string keys."
        )
    return osm_type, osm_id, dict(tags)


def _coordinate(lon: Any, lat: Any, label: str) -> list[float]:
    if (
        isinstance(lon, bool)
        or isinstance(lat, bool)
        or not isinstance(lon, (int, float))
        or not isinstance(lat, (int, float))
        or not math.isfinite(lon)
        or not math.isfinite(lat)
        or not -180 <= lon <= 180
        or not -90 <= lat <= 90
    ):
        raise ValueError(f"{label} must contain valid WGS84 longitude and latitude.")
    return [float(lon), float(lat)]


def _normalize_geometry(
    element: Mapping[str, Any], osm_type: str, tags: Mapping[str, Any]
) -> dict[str, Any]:
    if osm_type == "node":
        if "lat" not in element or "lon" not in element:
            raise ValueError("node is missing its 'lat' or 'lon' coordinate.")
        coordinates = _coordinate(element["lon"], element["lat"], "node")
        return {"type": "Point", "coordinates": coordinates}

    raw_geometry = element.get("geometry")
    if not isinstance(raw_geometry, list):
        raise TypeError(
            f"{osm_type} is missing a supported 'geometry' coordinate array."
        )

    coordinates: list[list[float]] = []
    for point_index, point in enumerate(raw_geometry):
        if not isinstance(point, Mapping) or "lat" not in point or "lon" not in point:
            raise ValueError(
                f"geometry coordinate {point_index} must be an object with 'lat' "
                "and 'lon'."
            )
        coordinates.append(
            _coordinate(
                point["lon"], point["lat"], f"geometry coordinate {point_index}"
            )
        )

    if len(coordinates) < 2:
        raise ValueError("line geometry must contain at least two coordinates.")

    is_green_space = any(tags.get(key) is not None for key in GREEN_TAGS)
    is_closed_ring = coordinates[0] == coordinates[-1]
    if is_green_space and is_closed_ring:
        if len(coordinates) < 4:
            raise ValueError("polygon ring must contain at least four coordinates.")
        return {"type": "Polygon", "coordinates": [coordinates]}
    return {"type": "LineString", "coordinates": coordinates}


def _feature_category(tags: Mapping[str, Any]) -> str:
    highway = tags.get("highway")
    is_green_space = any(tags.get(key) is not None for key in GREEN_TAGS)
    if highway in PEDESTRIAN_HIGHWAYS:
        category = "pedestrian_path"
    elif highway in ROAD_HIGHWAYS:
        category = "road"
    elif highway is not None:
        category = "other_highway"
    else:
        category = "green_space" if is_green_space else "other"

    if is_green_space and category != "green_space":
        return f"{category}_and_green_space"
    return category


def normalize_osm_document(
    document: Mapping[str, Any],
    *,
    source_type: str,
    source_filename: str | None,
    processed_at: datetime | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert valid OSM elements into deterministic RFC 7946 features."""
    validated = _validate_document(document)
    elements = validated["elements"]
    seen: set[tuple[str, int]] = set()
    features: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    duplicate_count = 0

    for index, element in enumerate(elements):
        osm_type, osm_id, tags = _validate_element(element, index)
        key = (osm_type, osm_id)
        if key in seen:
            duplicate_count += 1
            logger.warning("Skipping duplicate OSM element {} / {}", osm_type, osm_id)
            continue
        seen.add(key)

        try:
            geometry = _normalize_geometry(element, osm_type, tags)
        except (TypeError, ValueError) as exc:
            issue = {
                "osm_type": osm_type,
                "osm_id": osm_id,
                "reason": str(exc),
            }
            skipped.append(issue)
            logger.warning("Skipping OSM element {} / {}: {}", osm_type, osm_id, exc)
            continue

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "osm_type": osm_type,
                    "osm_id": osm_id,
                    "feature_category": _feature_category(tags),
                    "tags": tags,
                    "relevant_tags": {
                        key: tags[key] for key in RELEVANT_TAGS if key in tags
                    },
                    "source": {
                        "type": source_type,
                        "filename": source_filename,
                    },
                },
            }
        )

    features.sort(
        key=lambda feature: (
            feature["properties"]["osm_type"],
            feature["properties"]["osm_id"],
        )
    )
    osm3s = validated.get("osm3s") or {}
    osm_timestamp = osm3s.get("timestamp_osm_base")
    retrieval_date = None
    if isinstance(osm_timestamp, str):
        try:
            retrieval_date = datetime.fromisoformat(osm_timestamp).date().isoformat()
        except ValueError:
            logger.warning("Ignoring invalid OSM base timestamp: {}", osm_timestamp)

    run_timestamp = processed_at or datetime.now(UTC)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.replace(tzinfo=UTC)
    run_timestamp = run_timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")

    category_counts = Counter(
        feature["properties"]["feature_category"] for feature in features
    )
    if not elements and not skipped:
        outcome = "empty"
    elif skipped:
        outcome = "partial"
    else:
        outcome = "success"

    metadata: dict[str, Any] = {
        "source_type": source_type,
        "source_filename": source_filename,
        "retrieval_date": retrieval_date,
        "processing_timestamp": run_timestamp,
        "coordinate_reference_system": CRS,
        "processing_outcome": outcome,
        "feature_counts": {
            "input_elements": len(elements),
            "normalized_features": len(features),
            "duplicates_skipped": duplicate_count,
            "invalid_or_unsupported_geometry_skipped": len(skipped),
            "by_category": dict(sorted(category_counts.items())),
        },
        "skipped_elements": skipped,
        "attribution": "© OpenStreetMap contributors",
        "license": "Open Database License (ODbL)",
    }
    geojson = {
        "type": "FeatureCollection",
        "greenmiles_metadata": metadata,
        "features": features,
    }
    return geojson, metadata


def process_osm_data(
    document: Mapping[str, Any],
    output_path: Path,
    *,
    source_type: str,
    source_filename: str | None = None,
    source_path: Path | None = None,
    processed_at: datetime | None = None,
) -> IngestionResult:
    """Normalize OSM JSON-like data and write GeoJSON plus a metadata sidecar.

    ``source_path`` is only used to guard against accidentally overwriting input.
    A future network source can pass its decoded payload here without changing
    normalization or output behavior.
    """
    output_path = Path(output_path)
    metadata_path = output_path.with_suffix(".metadata.json")
    if source_path is not None:
        resolved_source = Path(source_path).resolve()
        for destination in (output_path, metadata_path):
            if destination.resolve() == resolved_source:
                raise ValueError("Processed output must not overwrite the raw source.")

    geojson, metadata = normalize_osm_document(
        document,
        source_type=source_type,
        source_filename=source_filename,
        processed_at=processed_at,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(geojson, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "OSM ingestion {}: {} features written to {}",
        metadata["processing_outcome"],
        metadata["feature_counts"]["normalized_features"],
        output_path,
    )
    return IngestionResult(output_path, metadata_path, metadata)


def ingest_local_file(
    input_path: Path,
    output_path: Path,
    *,
    processed_at: datetime | None = None,
) -> IngestionResult:
    """Read a local OSM JSON file and pass it through shared normalization."""
    source = LocalOSMJsonSource(Path(input_path))
    document = source.read()
    return process_osm_data(
        document,
        Path(output_path),
        source_type=source.source_type,
        source_filename=source.source_filename,
        source_path=source.path,
        processed_at=processed_at,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the documented local-fixture ingestion module entry point."""
    parser = argparse.ArgumentParser(description="Normalize a local OSM JSON export.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data/raw/osm/sample_manesar.json",
        help="saved OSM JSON file (default: data/raw/osm/sample_manesar.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data/processed/osm/sample_manesar.geojson",
        help="GeoJSON output path (default: data/processed/osm/sample_manesar.geojson)",
    )
    args = parser.parse_args(argv)

    config = load_config()
    log_directory = Path(config.logging.directory)
    if not log_directory.is_absolute():
        log_directory = PROJECT_ROOT / log_directory
    setup_logger(log_directory, config.logging.level)

    result = ingest_local_file(args.input, args.output)
    logger.info("Metadata written to {}", result.metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
