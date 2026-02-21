"""Tests for SchemaCache."""

from datetime import datetime, timedelta
from unittest.mock import patch

from jira_mcp_server.models import FieldSchema, FieldType
from jira_mcp_server.schema_cache import SchemaCache


def _make_field(key: str = "summary") -> FieldSchema:
    return FieldSchema(key=key, name="Summary", type=FieldType.STRING, required=True, custom=False)


class TestSchemaCache:
    def test_get_returns_none_for_missing(self) -> None:
        cache = SchemaCache()
        assert cache.get("PROJ", "Task") is None

    def test_set_and_get(self) -> None:
        cache = SchemaCache()
        fields = [_make_field()]
        cache.set("PROJ", "Task", fields)
        result = cache.get("PROJ", "Task")
        assert result is not None
        assert len(result) == 1
        assert result[0].key == "summary"

    def test_get_different_key_returns_none(self) -> None:
        cache = SchemaCache()
        cache.set("PROJ", "Task", [_make_field()])
        assert cache.get("PROJ", "Bug") is None

    def test_clear_specific_entry(self) -> None:
        cache = SchemaCache()
        cache.set("PROJ", "Task", [_make_field()])
        cache.set("PROJ", "Bug", [_make_field()])
        cache.clear("PROJ", "Task")
        assert cache.get("PROJ", "Task") is None
        assert cache.get("PROJ", "Bug") is not None

    def test_clear_nonexistent_entry(self) -> None:
        cache = SchemaCache()
        cache.clear("PROJ", "Task")

    def test_clear_all(self) -> None:
        cache = SchemaCache()
        cache.set("PROJ", "Task", [_make_field()])
        cache.set("PROJ", "Bug", [_make_field()])
        cache.clear_all()
        assert cache.get("PROJ", "Task") is None
        assert cache.get("PROJ", "Bug") is None

    def test_ttl_expiration(self) -> None:
        cache = SchemaCache(ttl_seconds=1)
        cache.set("PROJ", "Task", [_make_field()])
        expired_time = datetime.now() + timedelta(seconds=2)
        with patch("jira_mcp_server.schema_cache.datetime") as mock_dt:
            mock_dt.now.return_value = expired_time
            result = cache.get("PROJ", "Task")
        assert result is None

    def test_ttl_not_expired(self) -> None:
        cache = SchemaCache(ttl_seconds=3600)
        cache.set("PROJ", "Task", [_make_field()])
        result = cache.get("PROJ", "Task")
        assert result is not None

    def test_stats_tracking_hits(self) -> None:
        cache = SchemaCache()
        cache.set("PROJ", "Task", [_make_field()])
        cache.get("PROJ", "Task")
        cache.get("PROJ", "Task")
        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 0
        assert stats["total_entries"] == 1

    def test_stats_tracking_misses(self) -> None:
        cache = SchemaCache()
        cache.get("PROJ", "Task")
        cache.get("PROJ", "Bug")
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 2

    def test_stats_reset_on_clear_all(self) -> None:
        cache = SchemaCache()
        cache.set("PROJ", "Task", [_make_field()])
        cache.get("PROJ", "Task")
        cache.get("MISSING", "Bug")
        cache.clear_all()
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_entries"] == 0

    def test_expired_entry_counts_as_miss(self) -> None:
        cache = SchemaCache(ttl_seconds=1)
        cache.set("PROJ", "Task", [_make_field()])
        expired_time = datetime.now() + timedelta(seconds=2)
        with patch("jira_mcp_server.schema_cache.datetime") as mock_dt:
            mock_dt.now.return_value = expired_time
            cache.get("PROJ", "Task")
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0
