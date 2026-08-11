from __future__ import annotations

import json
import re
from pathlib import Path

from src.validation.validation_artifact import (
    ValidationArtifact,
)


_ARTIFACT_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
)


class ValidationArtifactStore:
    """
    Filesystem persistence layer for validation artifacts.

    Artifacts are immutable once written. Existing artifact IDs
    cannot be overwritten.
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

        if not self._root.exists():
            self._root.mkdir(
                parents=True,
                exist_ok=True,
            )

        if not self._root.is_dir():
            raise ValueError(
                "validation artifact root must be a directory"
            )

    @property
    def root(self) -> Path:
        return self._root

    def _validate_artifact_id(
        self,
        artifact_id: str,
    ) -> str:
        if not isinstance(artifact_id, str):
            raise TypeError(
                "artifact_id must be a string"
            )

        normalized = artifact_id.strip()

        if not normalized:
            raise ValueError(
                "artifact_id cannot be empty"
            )

        if not _ARTIFACT_ID_PATTERN.fullmatch(normalized):
            raise ValueError(
                "artifact_id contains unsafe characters"
            )

        return normalized

    def _path_for(
        self,
        artifact_id: str,
    ) -> Path:
        normalized = self._validate_artifact_id(
            artifact_id
        )

        return self._root / f"{normalized}.json"

    def save(
        self,
        artifact: ValidationArtifact,
        artifact_id: str,
    ) -> Path:
        if not isinstance(
            artifact,
            ValidationArtifact,
        ):
            raise TypeError(
                "artifact must be a ValidationArtifact"
            )

        path = self._path_for(artifact_id)

        if path.exists():
            raise FileExistsError(
                f"validation artifact already exists: "
                f"{artifact_id}"
            )

        payload = artifact.to_json()

        path.write_text(
            payload + "\n",
            encoding="utf-8",
        )

        return path

    def load(
        self,
        artifact_id: str,
    ) -> ValidationArtifact:
        path = self._path_for(artifact_id)

        if not path.exists():
            raise FileNotFoundError(
                f"validation artifact not found: "
                f"{artifact_id}"
            )

        try:
            payload = path.read_text(
                encoding="utf-8"
            )

            data = json.loads(payload)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"invalid validation artifact JSON: "
                f"{artifact_id}"
            ) from exc

        return ValidationArtifact.from_dict(data)

    def exists(
        self,
        artifact_id: str,
    ) -> bool:
        return self._path_for(artifact_id).exists()

    def list_artifacts(self) -> tuple[str, ...]:
        artifacts = sorted(
            path.stem
            for path in self._root.glob("*.json")
            if path.is_file()
        )

        return tuple(artifacts)


__all__ = [
    "ValidationArtifactStore",
]