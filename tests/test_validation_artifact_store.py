from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from src.validation.validation_artifact import (
    ValidationArtifact,
)
from src.validation.validation_artifact_store import (
    ValidationArtifactStore,
)


def make_artifact() -> ValidationArtifact:
    return ValidationArtifact(
        generated_at=datetime(
            2026,
            8,
            11,
            10,
            30,
            tzinfo=timezone.utc,
        ),
        horizon="LONG_TERM",
        validation_report={
            "average_return": Decimal("0.10"),
            "observations": 10,
        },
        stress_test_result={
            "passed": True,
        },
    )


def test_store_creates_missing_directory(
    tmp_path: Path,
):
    root = tmp_path / "validation"

    store = ValidationArtifactStore(root)

    assert root.exists()
    assert root.is_dir()
    assert store.root == root


def test_save_creates_json_artifact(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)
    artifact = make_artifact()

    path = store.save(
        artifact,
        "run-001",
    )

    assert path == tmp_path / "run-001.json"
    assert path.exists()
    assert path.suffix == ".json"


def test_save_and_load_round_trip(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)
    artifact = make_artifact()

    store.save(
        artifact,
        "run-001",
    )

    restored = store.load("run-001")

    assert restored.to_json() == artifact.to_json()


def test_duplicate_artifact_is_rejected(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)
    artifact = make_artifact()

    store.save(
        artifact,
        "run-001",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        store.save(
            artifact,
            "run-001",
        )


def test_missing_artifact_is_rejected(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match="not found",
    ):
        store.load("missing")


def test_exists(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)

    assert store.exists("run-001") is False

    store.save(
        make_artifact(),
        "run-001",
    )

    assert store.exists("run-001") is True


def test_list_artifacts_is_sorted(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)

    store.save(make_artifact(), "run-003")
    store.save(make_artifact(), "run-001")
    store.save(make_artifact(), "run-002")

    assert store.list_artifacts() == (
        "run-001",
        "run-002",
        "run-003",
    )


@pytest.mark.parametrize(
    "artifact_id",
    [
        "",
        " ",
        "../escape",
        "run/001",
        "run\\001",
        "run 001",
        "run$001",
    ],
)
def test_unsafe_artifact_ids_are_rejected(
    tmp_path: Path,
    artifact_id: str,
):
    store = ValidationArtifactStore(tmp_path)

    with pytest.raises(
        ValueError,
        match="unsafe|empty",
    ):
        store.exists(artifact_id)


def test_artifact_id_must_be_string(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)

    with pytest.raises(
        TypeError,
        match="artifact_id",
    ):
        store.exists(123)  # type: ignore[arg-type]


def test_invalid_json_is_rejected(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)

    (tmp_path / "broken.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="invalid validation artifact JSON",
    ):
        store.load("broken")


def test_non_artifact_object_cannot_be_saved(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)

    with pytest.raises(
        TypeError,
        match="ValidationArtifact",
    ):
        store.save(  # type: ignore[arg-type]
            {"invalid": True},
            "run-001",
        )


def test_existing_non_json_files_are_ignored(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)

    (tmp_path / "README.txt").write_text(
        "not an artifact",
        encoding="utf-8",
    )

    store.save(
        make_artifact(),
        "run-001",
    )

    assert store.list_artifacts() == (
        "run-001",
    )


def test_save_does_not_modify_artifact(
    tmp_path: Path,
):
    store = ValidationArtifactStore(tmp_path)
    artifact = make_artifact()

    before = artifact.to_json()

    store.save(
        artifact,
        "run-001",
    )

    assert artifact.to_json() == before