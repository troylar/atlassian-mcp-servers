"""Tests for FieldValidator."""

import pytest

from jira_mcp_server.models import FieldSchema, FieldType, FieldValidationError
from jira_mcp_server.validators import FieldValidator


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
