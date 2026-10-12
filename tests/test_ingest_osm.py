import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from greenmiles.ingest_osm import (
    LocalOSMJsonSource,
    OSMInputError,
    ingest_local_file,
    process_osm_data,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "data/raw/osm/sample_manesar.json"
FIXED_TIME = datetime(2026, 10, 12, 8, 0, tzinfo=UTC)


def _write_json(path: Path, document: object) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def _way(
    osm_id: int,
    *,
    tags: dict[str, str] | None = None,
    geometry: list[dict[str, float]] | None = None,
) -> dict[str, object]:
    return {
        "type": "way",
        "id": osm_id,
        "tags": tags or {"highway": "path"},
        "geometry": geometry
        if geometry is not None
        else [{"lat": 28.0, "lon": 76.0}, {"lat": 28.1, "lon": 76.1}],
    }


def test_actual_fixture_normalizes_paths_and_green_space(tmp_path: Path):
    source_bytes = FIXTURE_PATH.read_bytes()
    output = tmp_path / "osm" / "fixture.geojson"

    result = ingest_local_file(FIXTURE_PATH, output, processed_at=FIXED_TIME)

    geojson = json.loads(output.read_text(encoding="utf-8"))
    assert FIXTURE_PATH.read_bytes() == source_bytes
    assert geojson["type"] == "FeatureCollection"
    assert result.metadata["processing_outcome"] == "success"
    assert result.metadata["retrieval_date"] == "2026-10-12"
    assert result.metadata["coordinate_reference_system"] == "EPSG:4326"
    assert result.metadata["feature_counts"]["input_elements"] == 42
    assert result.metadata["feature_counts"]["normalized_features"] == 42
    assert result.metadata["feature_counts"]["by_category"] == {
        "green_space": 1,
        "road": 41,
    }

    road_feature = next(
        feature
        for feature in geojson["features"]
        if feature["properties"]["feature_category"] == "road"
    )
    park_feature = next(
        feature
        for feature in geojson["features"]
        if feature["properties"]["feature_category"] == "green_space"
    )
    assert road_feature["properties"]["osm_type"] == "way"
    assert road_feature["properties"]["osm_id"] == 639627336
    assert road_feature["properties"]["tags"]["highway"] == "service"
    assert road_feature["geometry"]["type"] == "LineString"
    assert road_feature["geometry"]["coordinates"][0] == [76.8167278, 28.2473252]
    assert park_feature["properties"]["osm_id"] == 1299461620
    assert park_feature["properties"]["tags"]["leisure"] == "park"
    assert park_feature["geometry"]["type"] == "Polygon"
    assert (
        park_feature["geometry"]["coordinates"][0][0]
        == park_feature["geometry"]["coordinates"][0][-1]
    )
    assert park_feature["properties"]["source"] == {
        "type": "local_osm_json",
        "filename": "sample_manesar.json",
    }

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata == result.metadata
    assert metadata["processing_timestamp"] == "2026-10-12T08:00:00Z"
    assert metadata["source_filename"] == "sample_manesar.json"
    assert metadata["attribution"] == "© OpenStreetMap contributors"
    assert metadata["license"] == "Open Database License (ODbL)"


def test_preserves_node_way_relation_and_both_categories(tmp_path: Path):
    document = {
        "elements": [
            {
                "type": "node",
                "id": 12,
                "lat": 28.0,
                "lon": 76.0,
                "tags": {"natural": "tree"},
            },
            _way(13, tags={"highway": "path", "leisure": "park"}),
            {
                "type": "relation",
                "id": 14,
                "tags": {
                    "route": "hiking",
                    "access": "yes",
                    "foot": "designated",
                    "surface": "gravel",
                },
                "geometry": [{"lat": 28.2, "lon": 76.2}, {"lat": 28.3, "lon": 76.3}],
            },
        ]
    }
    output = tmp_path / "mixed.geojson"

    result = process_osm_data(
        document,
        output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )
    features = json.loads(output.read_text(encoding="utf-8"))["features"]

    by_id = {feature["properties"]["osm_id"]: feature for feature in features}
    assert by_id[12]["properties"]["osm_type"] == "node"
    assert by_id[12]["geometry"] == {"type": "Point", "coordinates": [76.0, 28.0]}
    assert by_id[12]["properties"]["feature_category"] == "green_space"
    assert by_id[13]["properties"]["feature_category"] == (
        "pedestrian_path_and_green_space"
    )
    assert by_id[14]["properties"]["osm_type"] == "relation"
    assert by_id[14]["geometry"]["type"] == "LineString"
    assert by_id[14]["properties"]["relevant_tags"] == {
        "access": "yes",
        "foot": "designated",
        "surface": "gravel",
    }
    assert result.metadata["feature_counts"]["normalized_features"] == 3


@pytest.mark.parametrize(
    ("highway", "expected_category"),
    [
        ("residential", "road"),
        ("service", "road"),
        ("footway", "pedestrian_path"),
        ("path", "pedestrian_path"),
        ("steps", "other_highway"),
        ("track", "other_highway"),
        ("cycleway", "other_highway"),
    ],
)
def test_highway_category_preserves_original_tags_and_geometry(
    tmp_path: Path, highway: str, expected_category: str
):
    source_geometry = [
        {"lat": 28.0, "lon": 76.0},
        {"lat": 28.1, "lon": 76.1},
    ]
    source_tags = {"highway": highway, "surface": "gravel", "access": "private"}
    output = tmp_path / f"{highway}.geojson"

    result = process_osm_data(
        {
            "elements": [
                {
                    "type": "way",
                    "id": 100,
                    "tags": source_tags,
                    "geometry": source_geometry,
                }
            ]
        },
        output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )

    feature = json.loads(output.read_text(encoding="utf-8"))["features"][0]
    assert feature["properties"]["feature_category"] == expected_category
    assert feature["properties"]["osm_type"] == "way"
    assert feature["properties"]["osm_id"] == 100
    assert feature["properties"]["tags"] == source_tags
    assert feature["geometry"] == {
        "type": "LineString",
        "coordinates": [[76.0, 28.0], [76.1, 28.1]],
    }
    assert result.metadata["feature_counts"]["by_category"] == {expected_category: 1}


def test_green_space_way_remains_closed_polygon_with_source_data(tmp_path: Path):
    source_geometry = [
        {"lat": 28.0, "lon": 76.0},
        {"lat": 28.1, "lon": 76.0},
        {"lat": 28.1, "lon": 76.1},
        {"lat": 28.0, "lon": 76.0},
    ]
    source_tags = {"leisure": "park", "name": "Sample Park"}
    output = tmp_path / "park.geojson"

    result = process_osm_data(
        {
            "elements": [
                {
                    "type": "way",
                    "id": 101,
                    "tags": source_tags,
                    "geometry": source_geometry,
                }
            ]
        },
        output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )

    feature = json.loads(output.read_text(encoding="utf-8"))["features"][0]
    ring = feature["geometry"]["coordinates"][0]
    assert feature["properties"]["feature_category"] == "green_space"
    assert feature["properties"]["osm_type"] == "way"
    assert feature["properties"]["osm_id"] == 101
    assert feature["properties"]["tags"] == source_tags
    assert feature["geometry"]["type"] == "Polygon"
    assert ring == [[76.0, 28.0], [76.0, 28.1], [76.1, 28.1], [76.0, 28.0]]
    assert ring[0] == ring[-1]
    assert result.metadata["feature_counts"]["by_category"] == {"green_space": 1}


def test_duplicate_composite_identifiers_keep_first_element(tmp_path: Path):
    document = {
        "elements": [
            _way(7, tags={"highway": "path", "name": "first"}),
            _way(7, tags={"highway": "track", "name": "duplicate"}),
            {"type": "node", "id": 7, "lat": 28.0, "lon": 76.0},
        ]
    }
    output = tmp_path / "duplicates.geojson"

    result = process_osm_data(
        document,
        output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )
    features = json.loads(output.read_text(encoding="utf-8"))["features"]

    assert len(features) == 2
    assert result.metadata["feature_counts"]["duplicates_skipped"] == 1
    assert (
        next(
            feature["properties"]["tags"]["name"]
            for feature in features
            if feature["properties"]["osm_type"] == "way"
        )
        == "first"
    )


def test_missing_input_file_has_a_useful_error(tmp_path: Path):
    missing = tmp_path / "does-not-exist.json"

    with pytest.raises(FileNotFoundError, match="OSM input file not found"):
        LocalOSMJsonSource(missing).read()


def test_malformed_json_has_a_useful_error(tmp_path: Path):
    path = tmp_path / "broken.json"
    path.write_text('{"elements": [', encoding="utf-8")

    with pytest.raises(OSMInputError, match="Malformed JSON"):
        LocalOSMJsonSource(path).read()


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"elements": {}},
        {"elements": [None]},
        {"elements": [{"type": "area", "id": 1}]},
    ],
)
def test_unexpected_document_or_element_structure_is_rejected(document: object):
    with pytest.raises(OSMInputError):
        process_osm_data(
            document,  # type: ignore[arg-type]
            Path("unused.geojson"),
            source_type="test_payload",
            processed_at=FIXED_TIME,
        )


@pytest.mark.parametrize(
    ("element", "reason"),
    [
        ({"type": "way", "id": 1, "tags": {"highway": "path"}}, "missing"),
        (
            _way(2, geometry=[{"lat": 91.0, "lon": 76.0}, {"lat": 28.0, "lon": 76.0}]),
            "valid WGS84",
        ),
        (_way(3, geometry=[{"lat": 28.0, "lon": 76.0}]), "at least two"),
    ],
)
def test_missing_or_invalid_geometry_is_reported_and_skipped(
    tmp_path: Path, element: dict[str, object], reason: str
):
    output = tmp_path / "invalid-geometry.geojson"

    result = process_osm_data(
        {"elements": [element]},
        output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )

    geojson = json.loads(output.read_text(encoding="utf-8"))
    assert geojson["features"] == []
    assert result.metadata["processing_outcome"] == "partial"
    assert (
        result.metadata["feature_counts"]["invalid_or_unsupported_geometry_skipped"]
        == 1
    )
    assert reason in result.metadata["skipped_elements"][0]["reason"]


def test_empty_valid_dataset_is_not_an_ingestion_failure(tmp_path: Path):
    output = tmp_path / "empty.geojson"

    result = process_osm_data(
        {"elements": []},
        output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )

    assert json.loads(output.read_text(encoding="utf-8"))["features"] == []
    assert result.metadata["processing_outcome"] == "empty"
    assert result.metadata["feature_counts"]["input_elements"] == 0
    assert result.metadata["feature_counts"]["normalized_features"] == 0
    assert result.metadata["retrieval_date"] is None
    assert result.metadata_path.is_file()


def test_repeated_runs_with_same_input_and_timestamp_are_deterministic(tmp_path: Path):
    first_output = tmp_path / "first.geojson"
    second_output = tmp_path / "second.geojson"
    document = {
        "elements": [_way(9), _way(2, tags={"highway": "footway", "surface": "gravel"})]
    }

    process_osm_data(
        document,
        first_output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )
    process_osm_data(
        document,
        second_output,
        source_type="test_payload",
        processed_at=FIXED_TIME,
    )

    assert first_output.read_bytes() == second_output.read_bytes()
    assert (
        first_output.with_suffix(".metadata.json").read_bytes()
        == second_output.with_suffix(".metadata.json").read_bytes()
    )


def test_output_cannot_overwrite_raw_source(tmp_path: Path):
    source = tmp_path / "raw.json"
    _write_json(source, {"elements": []})
    original = source.read_bytes()

    with pytest.raises(ValueError, match="must not overwrite the raw source"):
        process_osm_data(
            {"elements": []},
            source,
            source_type="local_osm_json",
            source_path=source,
            processed_at=FIXED_TIME,
        )

    assert source.read_bytes() == original
