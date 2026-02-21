"""Field validation logic."""

from typing import Any, Dict, List, Optional, Tuple

from jira_mcp_server.models import FieldSchema, FieldType, FieldValidationError


class FieldValidator:
    """Validates Jira field values against field schemas."""

    def validate_required_fields(self, fields: Dict[str, Any], schema: List[FieldSchema]) -> List[str]:
        errors: List[str] = []
        required_keys = {f.key for f in schema if f.required}
        provided_keys = set(fields.keys())
        missing = required_keys - provided_keys
        if missing:
            missing_names = [f.name for f in schema if f.key in missing]
            errors.append(f"Missing required fields: {', '.join(missing_names)}")
        return errors

    def validate_custom_field_values(self, fields: Dict[str, Any], schema: List[FieldSchema]) -> List[str]:
        errors: List[str] = []
        schema_map = {f.key: f for f in schema}
        for field_key, value in fields.items():
            if field_key not in schema_map:
                continue
            field_schema = schema_map[field_key]
            is_valid, error_msg = self._validate_field_value(value, field_schema)
            if not is_valid and error_msg:
                errors.append(error_msg)
        return errors

    def _validate_field_value(self, value: Any, schema: FieldSchema) -> Tuple[bool, Optional[str]]:
        if schema.required and value is None:
            return False, f"Field '{schema.name}' is required"
        if value is None:
            return True, None

        if schema.type == FieldType.NUMBER:
            if not isinstance(value, (int, float)):
                return False, f"Field '{schema.name}' must be a number, got {type(value).__name__}"
        elif schema.type == FieldType.STRING:
            if not isinstance(value, str):
                return False, f"Field '{schema.name}' must be a string, got {type(value).__name__}"
        elif schema.type == FieldType.OPTION:
            if schema.allowed_values:
                if value not in schema.allowed_values:
                    allowed_str = ", ".join(schema.allowed_values)
                    return (
                        False,
                        f"Invalid value '{value}' for field '{schema.name}'. Allowed values: {allowed_str}",
                    )
        elif schema.type == FieldType.MULTI_SELECT:
            if not isinstance(value, list):
                return False, f"Field '{schema.name}' must be a list"
            if schema.allowed_values:
                for item in value:
                    if item not in schema.allowed_values:
                        allowed_str = ", ".join(schema.allowed_values)
                        return (
                            False,
                            f"Invalid value '{item}' in field '{schema.name}'. Allowed values: {allowed_str}",
                        )
        elif schema.type == FieldType.ARRAY:
            if not isinstance(value, list):
                return False, f"Field '{schema.name}' must be an array"
        elif schema.type == FieldType.DATE:
            if not isinstance(value, str):
                return False, f"Field '{schema.name}' must be a date string (ISO format)"
        elif schema.type == FieldType.DATETIME:
            if not isinstance(value, str):
                return False, f"Field '{schema.name}' must be a datetime string (ISO format)"

        return True, None

    def validate_fields(self, fields: Dict[str, Any], schema: List[FieldSchema]) -> None:
        errors: List[str] = []
        errors.extend(self.validate_required_fields(fields, schema))
        errors.extend(self.validate_custom_field_values(fields, schema))
        if errors:
            raise FieldValidationError("validation", "; ".join(errors))
