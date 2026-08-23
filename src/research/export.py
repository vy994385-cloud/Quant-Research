"""
Deterministic research export packages.

Bundles already-produced research artifacts into a portable
package of JSON / CSV files plus a verifiable manifest:

- every file is serialized canonically (sorted keys, stable row
  order) so the same inputs always produce byte-identical output;
- every file carries its byte count and SHA-256 checksum;
- the manifest itself is hashed, so a package can be verified as a
  whole;
- exports contain recorded facts only — no scores, rankings, or
  recommendations are added at export time.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


def _canonical_json(payload) -> str:
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        indent=2,
    ) + "\n"


def _canonical_csv(rows: list[dict]) -> str:
    if not rows:
        return ""

    fieldnames = sorted({key for row in rows for key in row})

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=fieldnames,
        lineterminator="\n",
    )
    writer.writeheader()

    ordered = sorted(
        rows,
        key=lambda row: tuple(str(row.get(f, "")) for f in fieldnames),
    )
    for row in ordered:
        writer.writerow(
            {
                field: (
                    ""
                    if row.get(field) is None
                    else str(row.get(field))
                )
                for field in fieldnames
            }
        )

    return buffer.getvalue()


class ExportEntry(BaseModel):
    """One exported file inside a package."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)


class ExportPackage(BaseModel):
    """
    A complete, self-describing export bundle.

    `files` maps filename -> text content. The manifest records the
    canonical serialization of every file together with the package
    digest.
    """

    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    files: dict[str, str] = Field(default_factory=dict)
    manifest: tuple[ExportEntry, ...] = ()
    package_sha256: str = Field(min_length=64, max_length=64)

    def verify(self) -> bool:
        """Recompute all checksums; True when nothing was altered."""

        for entry in self.manifest:
            content = self.files.get(entry.filename)
            if content is None:
                return False
            encoded = content.encode("utf-8")
            if len(encoded) != entry.bytes:
                return False
            if hashlib.sha256(encoded).hexdigest() != entry.sha256:
                return False

        digest = hashlib.sha256(
            "\n".join(
                f"{e.filename}:{e.sha256}" for e in self.manifest
            ).encode("utf-8")
        ).hexdigest()
        return digest == self.package_sha256


def build_export_package(
    payloads: dict[str, object],
    *,
    as_of: datetime,
) -> ExportPackage:
    """
    Build a deterministic export package.

    payloads maps filenames to content:
    - "*.json": pydantic models or JSON-serializable objects;
    - "*.csv": list of flat dicts (missing cells become empty).
    """

    _require_aware(as_of)

    if not payloads:
        raise ValueError("export package requires at least one payload")

    files: dict[str, str] = {}
    entries: list[ExportEntry] = []

    for filename in sorted(payloads):
        lower = filename.lower()
        payload = payloads[filename]

        if lower.endswith(".json"):
            content = _canonical_json(payload)
            media_type = "application/json"
        elif lower.endswith(".csv"):
            if not isinstance(payload, list):
                raise ValueError(
                    f"csv payload must be a list of dicts: {filename}"
                )
            content = _canonical_csv(payload)
            media_type = "text/csv"
        else:
            raise ValueError(
                f"unsupported export format (use .json or .csv): "
                f"{filename}"
            )

        encoded = content.encode("utf-8")
        files[filename] = content
        entries.append(
            ExportEntry(
                filename=filename,
                media_type=media_type,
                bytes=len(encoded),
                sha256=hashlib.sha256(encoded).hexdigest(),
            )
        )

    package_digest = hashlib.sha256(
        "\n".join(
            f"{e.filename}:{e.sha256}" for e in entries
        ).encode("utf-8")
    ).hexdigest()

    return ExportPackage(
        as_of=as_of,
        files=files,
        manifest=tuple(entries),
        package_sha256=package_digest,
    )


__all__ = [
    "ExportEntry",
    "ExportPackage",
    "build_export_package",
]
