"""Atomic local cache for validated Rebrickable relationship data."""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

from .relationships import (
    SOURCE_URL,
    PartRelationship,
    RelationshipDataError,
    RelationshipIndex,
    RelationshipType,
    parse_relationships,
)

CACHE_SCHEMA_VERSION = 1
DEFAULT_STALE_AFTER = timedelta(days=30)


class RelationshipCacheState(str, Enum):
    AVAILABLE = "available"
    NOT_DOWNLOADED = "not_downloaded"
    STALE = "stale"
    INVALID = "invalid"


@dataclass(frozen=True)
class RelationshipCacheMetadata:
    schema_version: int
    source_url: str
    downloaded_at: datetime
    sha256: str


@dataclass(frozen=True)
class RelationshipCacheResult:
    state: RelationshipCacheState
    index: RelationshipIndex | None = None
    metadata: RelationshipCacheMetadata | None = None


class RelationshipCache:
    """A sidecar cache that never makes ordinary inventory lookup depend on it."""

    def __init__(self, cache_directory: Path, filename: str = "relationships-v1.json") -> None:
        self.path = cache_directory / filename

    def load(
        self,
        *,
        now: datetime | None = None,
        stale_after: timedelta = DEFAULT_STALE_AFTER,
    ) -> RelationshipCacheResult:
        if not self.path.exists():
            return RelationshipCacheResult(RelationshipCacheState.NOT_DOWNLOADED)
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            metadata, relationships = _decode_cache(data)
        except (OSError, json.JSONDecodeError, RelationshipDataError, ValueError):
            return RelationshipCacheResult(RelationshipCacheState.INVALID)
        index = RelationshipIndex(relationships)
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
        state = (
            RelationshipCacheState.STALE
            if current_time - metadata.downloaded_at > stale_after
            else RelationshipCacheState.AVAILABLE
        )
        return RelationshipCacheResult(state, index, metadata)

    def replace_from_gzip(
        self,
        payload: bytes,
        *,
        source_url: str = SOURCE_URL,
        downloaded_at: datetime | None = None,
    ) -> RelationshipCacheMetadata:
        """Validate first, then atomically replace the cache with parsed records."""
        relationships = parse_relationships(io.BytesIO(payload))
        return self._write(
            relationships,
            source_url=source_url,
            downloaded_at=downloaded_at or datetime.now(timezone.utc),
            sha256=hashlib.sha256(payload).hexdigest(),
        )

    def _write(
        self,
        relationships: Iterable[PartRelationship],
        *,
        source_url: str,
        downloaded_at: datetime,
        sha256: str,
    ) -> RelationshipCacheMetadata:
        if not source_url.startswith("https://"):
            raise RelationshipDataError("Relationship cache source URL must use HTTPS.")
        if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256.lower()):
            raise RelationshipDataError("Relationship cache SHA-256 is invalid.")
        timestamp = (
            downloaded_at.astimezone(timezone.utc)
            if downloaded_at.tzinfo
            else downloaded_at.replace(tzinfo=timezone.utc)
        )
        records = sorted(
            set(relationships),
            key=lambda relationship: (
                relationship.relationship_type.value,
                relationship.child_part_num,
                relationship.parent_part_num,
            ),
        )
        metadata = RelationshipCacheMetadata(CACHE_SCHEMA_VERSION, source_url, timestamp, sha256.lower())
        data = {
            "schema_version": metadata.schema_version,
            "source_url": metadata.source_url,
            "downloaded_at": metadata.downloaded_at.isoformat().replace("+00:00", "Z"),
            "sha256": metadata.sha256,
            "relationships": [
                {
                    "rel_type": relationship.relationship_type.value,
                    "child_part_num": relationship.child_part_num,
                    "parent_part_num": relationship.parent_part_num,
                }
                for relationship in records
            ],
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
        return metadata


def _decode_cache(data: object) -> tuple[RelationshipCacheMetadata, tuple[PartRelationship, ...]]:
    if not isinstance(data, dict) or set(data) != {
        "schema_version",
        "source_url",
        "downloaded_at",
        "sha256",
        "relationships",
    }:
        raise RelationshipDataError("Relationship cache has an unexpected format.")
    if data["schema_version"] != CACHE_SCHEMA_VERSION:
        raise RelationshipDataError("Relationship cache schema version is unsupported.")
    source_url = data["source_url"]
    sha256 = data["sha256"]
    downloaded_at = data["downloaded_at"]
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise RelationshipDataError("Relationship cache source URL is invalid.")
    if not isinstance(sha256, str) or len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256.lower()):
        raise RelationshipDataError("Relationship cache SHA-256 is invalid.")
    if not isinstance(downloaded_at, str):
        raise RelationshipDataError("Relationship cache timestamp is invalid.")
    try:
        timestamp = datetime.fromisoformat(downloaded_at.replace("Z", "+00:00"))
    except ValueError:
        raise RelationshipDataError("Relationship cache timestamp is invalid.") from None
    if timestamp.tzinfo is None:
        raise RelationshipDataError("Relationship cache timestamp must include a timezone.")
    records = data["relationships"]
    if not isinstance(records, list):
        raise RelationshipDataError("Relationship cache records are invalid.")
    relationships: list[PartRelationship] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"rel_type", "child_part_num", "parent_part_num"}:
            raise RelationshipDataError("Relationship cache record is invalid.")
        try:
            relationship_type = RelationshipType(record["rel_type"])
            child = record["child_part_num"]
            parent = record["parent_part_num"]
            if not isinstance(child, str) or not isinstance(parent, str) or not child or not parent:
                raise ValueError
            if child != child.strip() or parent != parent.strip() or any(c.isspace() for c in child + parent):
                raise ValueError
        except (ValueError, TypeError):
            raise RelationshipDataError("Relationship cache record is invalid.") from None
        if child != parent:
            relationships.append(PartRelationship(relationship_type, child, parent))
    return (
        RelationshipCacheMetadata(
            CACHE_SCHEMA_VERSION,
            source_url,
            timestamp.astimezone(timezone.utc),
            sha256.lower(),
        ),
        tuple(
            sorted(
                set(relationships),
                key=lambda relationship: (
                    relationship.relationship_type.value,
                    relationship.child_part_num,
                    relationship.parent_part_num,
                ),
            )
        ),
    )
