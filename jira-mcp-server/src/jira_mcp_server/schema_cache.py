"""Schema caching with TTL logic."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from jira_mcp_server.models import CachedSchema, FieldSchema


class SchemaCache:
    """In-memory cache for Jira project schemas with TTL expiration."""

    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, CachedSchema] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._hits = 0
        self._misses = 0

    def _make_key(self, project_key: str, issue_type: str) -> str:
        return f"{project_key}:{issue_type}"

    def get(self, project_key: str, issue_type: str) -> Optional[List[FieldSchema]]:
        key = self._make_key(project_key, issue_type)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if datetime.now() >= entry.expires_at:
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return entry.fields

    def set(self, project_key: str, issue_type: str, fields: List[FieldSchema]) -> None:
        key = self._make_key(project_key, issue_type)
        now = datetime.now()
        cached_schema = CachedSchema(
            project_key=project_key,
            issue_type=issue_type,
            fields=fields,
            cached_at=now,
            expires_at=now + self._ttl,
        )
        self._cache[key] = cached_schema

    def clear(self, project_key: str, issue_type: str) -> None:
        key = self._make_key(project_key, issue_type)
        self._cache.pop(key, None)

    def clear_all(self) -> None:
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def get_stats(self) -> Dict[str, int]:
        return {
            "hits": self._hits,
            "misses": self._misses,
            "total_entries": len(self._cache),
        }
