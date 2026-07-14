"""Structured Rebrickable part-relationship data.

The public download is deliberately kept separate from set inventories.  It is
optional data: callers can use a missing or invalid relationship cache without
affecting ordinary offline element lookup.
"""

from __future__ import annotations

import csv
import gzip
import io
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import BinaryIO, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from . import __version__
SOURCE_URL = "https://cdn.rebrickable.com/media/downloads/part_relationships.csv.gz"
EXPECTED_HEADERS = ("rel_type", "child_part_num", "parent_part_num")
ALLOWED_DOWNLOAD_HOSTS = {"cdn.rebrickable.com"}
MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024


class RelationshipDataError(ValueError):
    """Raised when a relationship download or cache has an unsafe shape."""


class RelationshipDownloadError(RuntimeError):
    """Raised when the optional public relationship download is unavailable."""


class RelationshipType(str, Enum):
    """The relationship codes used by Rebrickable's public CSV download."""

    ALTERNATE = "A"
    SUBPART = "B"
    MOULD = "M"
    PRINT = "P"
    PAIR = "R"
    PATTERN = "T"


class RelationshipDirection(str, Enum):
    """Direction relative to the part that was looked up."""

    TO_PARENT = "to_parent"
    TO_CHILD = "to_child"


@dataclass(frozen=True, order=True)
class PartRelationship:
    """A directed source row: ``child_part_num`` relates to ``parent_part_num``."""

    relationship_type: RelationshipType
    child_part_num: str
    parent_part_num: str


@dataclass(frozen=True)
class RelatedDesign:
    """A deduplicated related code, retaining every observed source direction."""

    part_num: str
    relationship_type: RelationshipType
    directions: tuple[RelationshipDirection, ...]


@dataclass(frozen=True)
class RelatedDesigns:
    """Related designs grouped by Rebrickable's explicit relationship type."""

    groups: Mapping[RelationshipType, tuple[RelatedDesign, ...]]

    def for_type(self, relationship_type: RelationshipType) -> tuple[RelatedDesign, ...]:
        return self.groups.get(relationship_type, ())

    @property
    def alternates(self) -> tuple[RelatedDesign, ...]:
        return self.for_type(RelationshipType.ALTERNATE)

    @property
    def moulds(self) -> tuple[RelatedDesign, ...]:
        return self.for_type(RelationshipType.MOULD)


class RelationshipIndex:
    """Efficient forward and reverse indexes while retaining original direction."""

    def __init__(self, relationships: Iterable[PartRelationship]) -> None:
        unique = set(relationships)
        self.relationships = tuple(sorted(unique, key=_relationship_key))
        forward: dict[str, list[PartRelationship]] = defaultdict(list)
        reverse: dict[str, list[PartRelationship]] = defaultdict(list)
        for relationship in self.relationships:
            forward[relationship.child_part_num].append(relationship)
            reverse[relationship.parent_part_num].append(relationship)
        self.forward = {part_num: tuple(rows) for part_num, rows in forward.items()}
        self.reverse = {part_num: tuple(rows) for part_num, rows in reverse.items()}

    def related_designs(self, part_num: str) -> RelatedDesigns:
        """Return sorted, deduplicated related codes for both source directions."""
        value = _part_num(part_num, "part number")
        grouped: dict[RelationshipType, dict[str, set[RelationshipDirection]]] = defaultdict(
            lambda: defaultdict(set)
        )
        for relationship in self.forward.get(value, ()):
            grouped[relationship.relationship_type][relationship.parent_part_num].add(
                RelationshipDirection.TO_PARENT
            )
        for relationship in self.reverse.get(value, ()):
            grouped[relationship.relationship_type][relationship.child_part_num].add(
                RelationshipDirection.TO_CHILD
            )
        return RelatedDesigns(
            {
                relationship_type: tuple(
                    RelatedDesign(
                        related_part_num,
                        relationship_type,
                        tuple(sorted(directions, key=lambda direction: direction.value)),
                    )
                    for related_part_num, directions in sorted(by_part.items())
                )
                for relationship_type, by_part in sorted(grouped.items(), key=lambda item: item[0].value)
            }
        )


def _part_num(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise RelationshipDataError(f"Relationship {field} must be text.")
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise RelationshipDataError(f"Relationship {field} must not be empty or contain whitespace.")
    return value


def _relationship_key(relationship: PartRelationship) -> tuple[str, str, str]:
    return (
        relationship.relationship_type.value,
        relationship.child_part_num,
        relationship.parent_part_num,
    )


def parse_relationships(stream: BinaryIO) -> tuple[PartRelationship, ...]:
    """Strictly parse a gzipped Rebrickable ``part_relationships.csv`` stream."""
    try:
        with gzip.GzipFile(fileobj=stream, mode="rb") as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                reader = csv.DictReader(text, strict=True)
                if tuple(reader.fieldnames or ()) != EXPECTED_HEADERS:
                    raise RelationshipDataError(
                        "Relationship CSV headers must be " + ", ".join(EXPECTED_HEADERS) + "."
                    )
                relationships: set[PartRelationship] = set()
                for row_number, row in enumerate(reader, start=2):
                    if None in row or any(row.get(header) is None for header in EXPECTED_HEADERS):
                        raise RelationshipDataError(f"Relationship CSV row {row_number} has the wrong number of columns.")
                    try:
                        relationship_type = RelationshipType(str(row["rel_type"]))
                    except ValueError:
                        raise RelationshipDataError(
                            f"Relationship CSV row {row_number} has an unknown relationship type."
                        ) from None
                    child = _part_num(row["child_part_num"], "child part number")
                    parent = _part_num(row["parent_part_num"], "parent part number")
                    if child == parent:
                        continue
                    relationships.add(PartRelationship(relationship_type, child, parent))
    except RelationshipDataError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise RelationshipDataError("Relationship data is not a valid gzip CSV file.") from exc
    return tuple(sorted(relationships, key=_relationship_key))


def load_relationships(path: Path) -> tuple[PartRelationship, ...]:
    """Load and validate a relationship download from disk."""
    try:
        with path.open("rb") as stream:
            return parse_relationships(stream)
    except OSError as exc:
        raise RelationshipDataError(f"Could not read relationship data at {path}.") from exc


def download_relationship_data() -> bytes:
    """Fetch the public relationship CSV without using an API key."""
    request = Request(SOURCE_URL, headers={"User-Agent": f"lego-element-lookup/{__version__}"})
    try:
        with urlopen(request, timeout=30) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else SOURCE_URL
            parsed = urlparse(final_url)
            if parsed.scheme != "https" or parsed.hostname not in ALLOWED_DOWNLOAD_HOSTS:
                raise RelationshipDownloadError("Related-design data returned an unsafe download URL.")
            payload = response.read(MAX_DOWNLOAD_BYTES + 1)
    except RelationshipDownloadError:
        raise
    except HTTPError as exc:
        raise RelationshipDownloadError(f"Related-design data returned HTTP {exc.code}.") from None
    except (URLError, TimeoutError, OSError):
        raise RelationshipDownloadError("Related-design data is unavailable offline.") from None
    if len(payload) > MAX_DOWNLOAD_BYTES:
        raise RelationshipDownloadError("Related-design data is unexpectedly large.")
    return payload
