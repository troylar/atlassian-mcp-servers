"""Response formatters for token-efficient output."""

from typing import Any, Dict, Optional

from confluence_mcp_server.config import ConfluenceConfig

_DEFAULT_MAX_DESC = 500


def _resolve_detail(detail: Optional[str], config: Optional[ConfluenceConfig]) -> str:
    if detail is not None:
        if detail not in ("summary", "full"):
            raise ValueError(f"Invalid detail level: {detail!r}. Must be 'summary' or 'full'.")
        return detail
    if config is None:
        return "full"
    return config.default_detail


def _max_desc(config: Optional[ConfluenceConfig]) -> int:
    return config.max_description_length if config else _DEFAULT_MAX_DESC


def _links(config: Optional[ConfluenceConfig]) -> bool:
    return config.include_links if config else False


def truncate_text(text: Optional[str], max_length: int) -> Optional[str]:
    if text is None:
        return None
    if max_length == 0:
        return text
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def _extract_name(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get("displayName") or obj.get("name") or obj.get("title")
    return str(obj)


def _extract_body_text(raw: Dict[str, Any]) -> Optional[str]:
    body = raw.get("body", {})
    storage = body.get("storage", {})
    value: Optional[str] = storage.get("value")
    return value


def format_page(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "type": raw.get("type"),
        "status": raw.get("status"),
        "space": _extract_name(raw.get("space")),
    }
    version = raw.get("version")
    if version and isinstance(version, dict):
        result["version"] = version.get("number")
    body_text = _extract_body_text(raw)
    if body_text is not None:
        result["body"] = truncate_text(body_text, _max_desc(config))
    if _links(config):
        result["self"] = raw.get("_links", {}).get("self")
        result["webui"] = raw.get("_links", {}).get("webui")
    return result


def format_pages(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    results = raw.get("results", [])
    return {
        "size": raw.get("size", len(results)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "results": [format_page(p, config) for p in results],
    }


def format_space(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "key": raw.get("key"),
        "name": raw.get("name"),
        "type": raw.get("type"),
    }
    desc = raw.get("description")
    if isinstance(desc, dict):
        plain = desc.get("plain", {})
        if isinstance(plain, dict) and plain.get("value"):
            result["description"] = truncate_text(plain["value"], _max_desc(config))
    elif isinstance(desc, str):
        result["description"] = truncate_text(desc, _max_desc(config))
    if _links(config):
        result["self"] = raw.get("_links", {}).get("self")
    return result


def format_spaces(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    results = raw.get("results", [])
    return {
        "size": raw.get("size", len(results)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "results": [format_space(s, config) for s in results],
    }


def format_comment(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "author": _extract_name(raw.get("author") or raw.get("by")),
        "created": raw.get("created") or raw.get("when"),
    }
    body_text = _extract_body_text(raw)
    if body_text is not None:
        result["body"] = truncate_text(body_text, _max_desc(config))
    if _links(config):
        result["self"] = raw.get("_links", {}).get("self")
    return result


def format_comments(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    results = raw.get("results", [])
    return {
        "size": raw.get("size", len(results)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "results": [format_comment(c, config) for c in results],
    }


def format_attachment(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    extensions = raw.get("extensions", {})
    result: Dict[str, Any] = {
        "id": raw.get("id"),
        "title": raw.get("title"),
        "mediaType": extensions.get("mediaType") if isinstance(extensions, dict) else None,
        "fileSize": extensions.get("fileSize") if isinstance(extensions, dict) else None,
    }
    if _links(config):
        result["self"] = raw.get("_links", {}).get("self")
        result["download"] = raw.get("_links", {}).get("download")
    return result


def format_attachments(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    results = raw.get("results", [])
    return {
        "size": raw.get("size", len(results)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "results": [format_attachment(a, config) for a in results],
    }


def format_user(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "accountId": raw.get("accountId") or raw.get("userKey"),
        "displayName": raw.get("displayName"),
        "email": raw.get("email"),
        "type": raw.get("type"),
    }
    if _links(config):
        result["self"] = raw.get("_links", {}).get("self")
    return result


def format_search_result(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    content = raw.get("content", {})
    result: Dict[str, Any] = {
        "id": content.get("id"),
        "title": content.get("title") or raw.get("title"),
        "type": content.get("type"),
        "status": content.get("status"),
        "space": _extract_name(content.get("space")),
        "excerpt": truncate_text(raw.get("excerpt"), _max_desc(config)),
    }
    if _links(config):
        result["url"] = raw.get("url")
    return result


def format_search_results(raw: Dict[str, Any], config: Optional[ConfluenceConfig]) -> Dict[str, Any]:
    results = raw.get("results", [])
    return {
        "totalSize": raw.get("totalSize", len(results)),
        "size": raw.get("size", len(results)),
        "start": raw.get("start", 0),
        "limit": raw.get("limit", 0),
        "results": [format_search_result(r, config) for r in results],
    }


def format_label(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": raw.get("name"),
        "prefix": raw.get("prefix"),
        "id": raw.get("id"),
    }


def format_labels(raw: Dict[str, Any]) -> Dict[str, Any]:
    results = raw.get("results", [])
    return {
        "size": raw.get("size", len(results)),
        "results": [format_label(lb) for lb in results],
    }
