"""Tests for FieldValidator and security validators."""

import pytest

from jira_mcp_server.models import FieldSchema, FieldType, FieldValidationError
from jira_mcp_server.validators import (
    FieldValidator,
    _safe_error_text,
    validate_enum,
    validate_file_path,
    validate_issue_key,
    validate_max_results,
    validate_numeric_id,
    validate_project_key,
)


def _schema(
    key: str = "test",
    name: str = "Test",
    field_type: FieldType = FieldType.STRING,
    required: bool = False,
    allowed_values: list[str] | None = None,
) -> FieldSchema:
    return FieldSchema(
        key=key, name=name, type=field_type, required=required, custom=False, allowed_values=allowed_values
    )


class TestRequiredFieldValidation:
    def test_no_missing_fields(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="summary", required=True)]
        errors = validator.validate_required_fields({"summary": "test"}, schema)
        assert errors == []

    def test_missing_required_field(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="summary", name="Summary", required=True)]
        errors = validator.validate_required_fields({}, schema)
        assert len(errors) == 1
        assert "Summary" in errors[0]

    def test_optional_field_not_required(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="description", required=False)]
        errors = validator.validate_required_fields({}, schema)
        assert errors == []


class TestTypeValidation:
    def test_number_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="num", field_type=FieldType.NUMBER)]
        errors = validator.validate_custom_field_values({"num": 42}, schema)
        assert errors == []

    def test_number_float_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="num", field_type=FieldType.NUMBER)]
        errors = validator.validate_custom_field_values({"num": 3.14}, schema)
        assert errors == []

    def test_number_invalid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="num", name="Number", field_type=FieldType.NUMBER)]
        errors = validator.validate_custom_field_values({"num": "not a number"}, schema)
        assert len(errors) == 1
        assert "must be a number" in errors[0]

    def test_string_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="text", field_type=FieldType.STRING)]
        errors = validator.validate_custom_field_values({"text": "hello"}, schema)
        assert errors == []

    def test_string_invalid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="text", name="Text", field_type=FieldType.STRING)]
        errors = validator.validate_custom_field_values({"text": 123}, schema)
        assert len(errors) == 1
        assert "must be a string" in errors[0]

    def test_option_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="priority", field_type=FieldType.OPTION, allowed_values=["High", "Low"])]
        errors = validator.validate_custom_field_values({"priority": "High"}, schema)
        assert errors == []

    def test_option_invalid_value(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="priority", name="Priority", field_type=FieldType.OPTION, allowed_values=["High", "Low"])]
        errors = validator.validate_custom_field_values({"priority": "Invalid"}, schema)
        assert len(errors) == 1
        assert "Invalid value" in errors[0]

    def test_option_no_allowed_values(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="priority", field_type=FieldType.OPTION)]
        errors = validator.validate_custom_field_values({"priority": "anything"}, schema)
        assert errors == []

    def test_array_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="labels", field_type=FieldType.ARRAY)]
        errors = validator.validate_custom_field_values({"labels": ["a", "b"]}, schema)
        assert errors == []

    def test_array_invalid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="labels", name="Labels", field_type=FieldType.ARRAY)]
        errors = validator.validate_custom_field_values({"labels": "not-a-list"}, schema)
        assert len(errors) == 1
        assert "must be an array" in errors[0]

    def test_multiselect_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="ms", field_type=FieldType.MULTI_SELECT, allowed_values=["A", "B"])]
        errors = validator.validate_custom_field_values({"ms": ["A"]}, schema)
        assert errors == []

    def test_multiselect_not_list(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="ms", name="Multi", field_type=FieldType.MULTI_SELECT)]
        errors = validator.validate_custom_field_values({"ms": "A"}, schema)
        assert len(errors) == 1
        assert "must be a list" in errors[0]

    def test_multiselect_invalid_value(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="ms", name="Multi", field_type=FieldType.MULTI_SELECT, allowed_values=["A", "B"])]
        errors = validator.validate_custom_field_values({"ms": ["A", "C"]}, schema)
        assert len(errors) == 1
        assert "Invalid value 'C'" in errors[0]

    def test_multiselect_no_allowed_values(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="ms", field_type=FieldType.MULTI_SELECT)]
        errors = validator.validate_custom_field_values({"ms": ["anything"]}, schema)
        assert errors == []

    def test_date_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="dt", field_type=FieldType.DATE)]
        errors = validator.validate_custom_field_values({"dt": "2024-01-01"}, schema)
        assert errors == []

    def test_date_invalid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="dt", name="Date", field_type=FieldType.DATE)]
        errors = validator.validate_custom_field_values({"dt": 123}, schema)
        assert len(errors) == 1
        assert "must be a date string" in errors[0]

    def test_datetime_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="dtt", field_type=FieldType.DATETIME)]
        errors = validator.validate_custom_field_values({"dtt": "2024-01-01T00:00:00"}, schema)
        assert errors == []

    def test_datetime_invalid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="dtt", name="DateTime", field_type=FieldType.DATETIME)]
        errors = validator.validate_custom_field_values({"dtt": 123}, schema)
        assert len(errors) == 1
        assert "must be a datetime string" in errors[0]

    def test_user_type_passes(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="user", field_type=FieldType.USER)]
        errors = validator.validate_custom_field_values({"user": "john"}, schema)
        assert errors == []

    def test_none_value_required_field(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="field", name="Field", required=True)]
        errors = validator.validate_custom_field_values({"field": None}, schema)
        assert len(errors) == 1
        assert "is required" in errors[0]

    def test_none_value_optional_field(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="field", required=False)]
        errors = validator.validate_custom_field_values({"field": None}, schema)
        assert errors == []

    def test_unknown_field_skipped(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="summary")]
        errors = validator.validate_custom_field_values({"unknown_field": "value"}, schema)
        assert errors == []


class TestValidateFields:
    def test_all_valid(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="summary", name="Summary", required=True, field_type=FieldType.STRING)]
        validator.validate_fields({"summary": "test"}, schema)

    def test_raises_on_missing_required(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="summary", name="Summary", required=True)]
        with pytest.raises(FieldValidationError, match="Missing required"):
            validator.validate_fields({}, schema)

    def test_raises_on_type_error(self) -> None:
        validator = FieldValidator()
        schema = [_schema(key="num", name="Number", field_type=FieldType.NUMBER, required=False)]
        with pytest.raises(FieldValidationError, match="must be a number"):
            validator.validate_fields({"num": "not-a-number"}, schema)

    def test_combines_errors(self) -> None:
        validator = FieldValidator()
        schema = [
            _schema(key="summary", name="Summary", required=True),
            _schema(key="num", name="Number", field_type=FieldType.NUMBER, required=False),
        ]
        with pytest.raises(FieldValidationError) as exc_info:
            validator.validate_fields({"num": "bad"}, schema)
        assert "Summary" in str(exc_info.value)
        assert "must be a number" in str(exc_info.value)


# --- Security validator tests ---


class TestValidateIssueKey:
    def test_valid_simple(self) -> None:
        assert validate_issue_key("PROJ-1") == "PROJ-1"

    def test_valid_long_project(self) -> None:
        assert validate_issue_key("MY_PROJECT2-999") == "MY_PROJECT2-999"

    def test_valid_strips_whitespace(self) -> None:
        assert validate_issue_key("  PROJ-42  ") == "PROJ-42"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_issue_key("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_issue_key("   ")

    def test_exceeds_max_length(self) -> None:
        long_key = "A" * 200 + "-1" + "0" * 100
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_issue_key(long_key)

    def test_lowercase_rejected(self) -> None:
        with pytest.raises(ValueError, match="must match format"):
            validate_issue_key("proj-1")

    def test_missing_dash_rejected(self) -> None:
        with pytest.raises(ValueError, match="must match format"):
            validate_issue_key("PROJ1")

    def test_missing_number_rejected(self) -> None:
        with pytest.raises(ValueError, match="must match format"):
            validate_issue_key("PROJ-")

    def test_custom_name_in_error(self) -> None:
        with pytest.raises(ValueError, match="my_key must not be empty"):
            validate_issue_key("", name="my_key")


class TestValidateProjectKey:
    def test_valid_simple(self) -> None:
        assert validate_project_key("PROJ") == "PROJ"

    def test_valid_with_digits_underscore(self) -> None:
        assert validate_project_key("MY_PROJ2") == "MY_PROJ2"

    def test_valid_strips_whitespace(self) -> None:
        assert validate_project_key("  ABC  ") == "ABC"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_project_key("")

    def test_exceeds_max_length(self) -> None:
        with pytest.raises(ValueError, match="exceeds maximum length"):
            validate_project_key("A" * 256)

    def test_lowercase_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_project_key("proj")

    def test_starts_with_digit_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be uppercase"):
            validate_project_key("1PROJ")

    def test_custom_name_in_error(self) -> None:
        with pytest.raises(ValueError, match="pk must not be empty"):
            validate_project_key("", name="pk")


class TestValidateNumericId:
    def test_valid(self) -> None:
        assert validate_numeric_id("12345") == "12345"

    def test_valid_strips_whitespace(self) -> None:
        assert validate_numeric_id("  99  ") == "99"

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_numeric_id("")

    def test_non_numeric_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a numeric string"):
            validate_numeric_id("abc")

    def test_mixed_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a numeric string"):
            validate_numeric_id("12abc")

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must be a numeric string"):
            validate_numeric_id("-1")


class TestValidateMaxResults:
    def test_normal_value(self) -> None:
        assert validate_max_results(50) == 50

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be negative"):
            validate_max_results(-1)

    def test_caps_at_default_ceiling(self) -> None:
        assert validate_max_results(200) == 100

    def test_caps_at_custom_ceiling(self) -> None:
        assert validate_max_results(50, ceiling=25) == 25

    def test_zero_allowed(self) -> None:
        assert validate_max_results(0) == 0

    def test_exact_ceiling_not_capped(self) -> None:
        assert validate_max_results(100) == 100


class TestValidateFilePath:
    def test_valid_file(self, tmp_path: pytest.TempPathFactory) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = validate_file_path(str(f))
        assert result == str(f.resolve())

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_file_path("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            validate_file_path("   ")

    def test_traversal_rejected(self, tmp_path: pytest.TempPathFactory) -> None:
        with pytest.raises(ValueError, match="path traversal"):
            validate_file_path(str(tmp_path / ".." / "etc" / "passwd"))

    def test_nonexistent_raises(self) -> None:
        with pytest.raises(ValueError, match="File not found"):
            validate_file_path("/nonexistent/path/file.txt")

    def test_directory_rejected(self, tmp_path: pytest.TempPathFactory) -> None:
        with pytest.raises(ValueError, match="not a regular file"):
            validate_file_path(str(tmp_path))


class TestValidateEnum:
    def test_valid_exact_case(self) -> None:
        allowed = frozenset({"active", "closed", "future"})
        assert validate_enum("active", "state", allowed) == "active"

    def test_case_insensitive_returns_original(self) -> None:
        allowed = frozenset({"Active", "Closed"})
        assert validate_enum("active", "state", allowed) == "Active"

    def test_invalid_value_raises(self) -> None:
        allowed = frozenset({"active", "closed"})
        with pytest.raises(ValueError, match="must be one of"):
            validate_enum("unknown", "state", allowed)

    def test_empty_raises(self) -> None:
        allowed = frozenset({"active"})
        with pytest.raises(ValueError, match="must not be empty"):
            validate_enum("", "state", allowed)

    def test_whitespace_only_raises(self) -> None:
        allowed = frozenset({"active"})
        with pytest.raises(ValueError, match="must not be empty"):
            validate_enum("   ", "state", allowed)

    def test_strips_whitespace(self) -> None:
        allowed = frozenset({"active"})
        assert validate_enum("  active  ", "state", allowed) == "active"


class TestSafeErrorText:
    def test_short_text_unchanged(self) -> None:
        assert _safe_error_text("simple error") == "simple error"

    def test_truncates_long_text(self) -> None:
        long_text = "x" * 500
        result = _safe_error_text(long_text)
        assert len(result) == 200

    def test_custom_max_len(self) -> None:
        result = _safe_error_text("abcdef", max_len=3)
        assert result == "abc"

    def test_redacts_bearer_token(self) -> None:
        text = "Error: Bearer eyJhbGciOiJIUzI1NiJ9 was invalid"
        result = _safe_error_text(text)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result
        assert "[REDACTED]" in result

    def test_redacts_basic_auth(self) -> None:
        text = "Auth failed: Basic dXNlcjpwYXNz in header"
        result = _safe_error_text(text)
        assert "dXNlcjpwYXNz" not in result
        assert "[REDACTED]" in result
