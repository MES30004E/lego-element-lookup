from __future__ import annotations

import gzip
import io
import json
from datetime import UTC, datetime, timedelta

import pytest

from lego_element_lookup.lookup import find_matches
from lego_element_lookup.relationship_cache import RelationshipCache, RelationshipCacheState
from lego_element_lookup.relationships import (
    RelationshipDataError,
    RelationshipDirection,
    RelationshipIndex,
    RelationshipType,
    parse_relationships,
)


def compressed_csv(rows: list[str], header: str = "rel_type,child_part_num,parent_part_num") -> bytes:
    return gzip.compress((header + "\n" + "\n".join(rows) + "\n").encode("utf-8"))


def test_valid_relationship_types_are_grouped_and_reverse_indexed():
    relationships = parse_relationships(
        io.BytesIO(
            compressed_csv(
                [
                    "A,alternate,parent",
                    "M,mould,parent",
                    "P,print,parent",
                    "T,pattern,parent",
                    "R,pair,parent",
                    "B,subpart,parent",
                ]
            )
        )
    )
    index = RelationshipIndex(relationships)
    grouped = index.related_designs("parent")

    assert [(kind.value, item.part_num, item.directions) for kind, items in grouped.groups.items() for item in items] == [
        ("A", "alternate", (RelationshipDirection.TO_CHILD,)),
        ("B", "subpart", (RelationshipDirection.TO_CHILD,)),
        ("M", "mould", (RelationshipDirection.TO_CHILD,)),
        ("P", "print", (RelationshipDirection.TO_CHILD,)),
        ("R", "pair", (RelationshipDirection.TO_CHILD,)),
        ("T", "pattern", (RelationshipDirection.TO_CHILD,)),
    ]
    assert index.related_designs("alternate").alternates[0].part_num == "parent"
    assert index.related_designs("alternate").alternates[0].directions == (RelationshipDirection.TO_PARENT,)


def test_duplicates_and_self_references_are_ignored_safely():
    relationships = parse_relationships(io.BytesIO(compressed_csv(["A,child,parent", "A,child,parent", "M,self,self"])))
    assert len(relationships) == 1
    assert RelationshipIndex(relationships).related_designs("parent").alternates[0].part_num == "child"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"not gzip", "valid gzip CSV"),
        (compressed_csv(["A,child,parent"], "type,child,parent"), "headers"),
        (compressed_csv(["A,child,parent,extra"]), "wrong number of columns"),
        (compressed_csv(["Z,child,parent"]), "unknown relationship type"),
        (compressed_csv(["A,,parent"]), "must not be empty"),
    ],
)
def test_malformed_relationship_data_is_rejected(payload, message):
    with pytest.raises(RelationshipDataError, match=message):
        parse_relationships(io.BytesIO(payload))


def test_live_example_records_are_indexed_by_their_actual_source_direction():
    # Records observed in Rebrickable's 2026-07-13 public CSV download.
    index = RelationshipIndex(
        parse_relationships(
            io.BytesIO(compressed_csv(["M,62712,57910", "M,92013,57910", "A,67696,57910"]))
        )
    )
    related = index.related_designs("57910")
    assert [item.part_num for item in related.alternates] == ["67696"]
    assert [item.part_num for item in related.moulds] == ["62712", "92013"]
    assert index.forward["67696"][0].relationship_type is RelationshipType.ALTERNATE


def test_cache_states_and_metadata(tmp_path):
    cache = RelationshipCache(tmp_path)
    assert cache.load().state is RelationshipCacheState.NOT_DOWNLOADED

    payload = compressed_csv(["A,child,parent"])
    timestamp = datetime(2026, 7, 13, tzinfo=UTC)
    metadata = cache.replace_from_gzip(payload, downloaded_at=timestamp)
    loaded = cache.load(now=timestamp + timedelta(days=1))
    assert loaded.state is RelationshipCacheState.AVAILABLE
    assert loaded.metadata == metadata
    assert loaded.index is not None
    assert [item.part_num for item in loaded.index.related_designs("parent").alternates] == ["child"]
    assert cache.load(now=timestamp + timedelta(days=31)).state is RelationshipCacheState.STALE


def test_cache_replacement_is_atomic_when_new_data_is_invalid(tmp_path):
    cache = RelationshipCache(tmp_path)
    cache.replace_from_gzip(compressed_csv(["A,old,parent"]))
    with pytest.raises(RelationshipDataError):
        cache.replace_from_gzip(b"not gzip")
    loaded = cache.load()
    assert loaded.state is RelationshipCacheState.AVAILABLE
    assert loaded.index is not None
    assert [item.part_num for item in loaded.index.related_designs("parent").alternates] == ["old"]


def test_invalid_cache_is_reported_without_raising(tmp_path):
    cache = RelationshipCache(tmp_path)
    cache.path.parent.mkdir(parents=True, exist_ok=True)
    cache.path.write_text(json.dumps({"not": "a cache"}), encoding="utf-8")
    assert cache.load().state is RelationshipCacheState.INVALID


def test_missing_relationship_data_does_not_affect_inventory_lookup(entries, tmp_path):
    assert RelationshipCache(tmp_path).load().state is RelationshipCacheState.NOT_DOWNLOADED
    assert find_matches(entries, "6212040")[0].part_code == "35480"
