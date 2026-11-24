from __future__ import annotations

from typing import Any

from epscad.loader import load_json
from epscad.schema import ValidationMessage, project_schema_for_profile


def validate_schema(spec: dict[str, Any]) -> list[ValidationMessage]:
    profile = str(spec.get("machine", {}).get("profile", ""))
    try:
        schema_path = project_schema_for_profile(profile)
    except ValueError as exc:
        return [ValidationMessage("error", "unsupported_machine_profile", str(exc), "machine.profile")]
    schema = load_json(schema_path)
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return _fallback_validate_schema(spec, schema)

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(spec), key=lambda item: list(item.absolute_path))
    messages = []
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path)
        messages.append(ValidationMessage("error", "schema_error", error.message, path))
    return messages


def _fallback_validate_schema(spec: dict[str, Any], schema: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    def walk(value: Any, node: dict[str, Any], path: str) -> None:
        if "const" in node and value != node["const"]:
            messages.append(ValidationMessage("error", "schema_const", f"expected {node['const']!r}", path))
        if "enum" in node and value not in node["enum"]:
            messages.append(ValidationMessage("error", "schema_enum", f"{value!r} not in {node['enum']}", path))
        expected_type = node.get("type")
        if expected_type and not _matches_type(value, expected_type):
            messages.append(ValidationMessage("error", "schema_type", f"expected type {expected_type}", path))
            return
        if isinstance(value, dict):
            required = node.get("required", [])
            for key in required:
                if key not in value:
                    messages.append(ValidationMessage("error", "schema_required", f"missing required field {key}", path))
            properties = node.get("properties", {})
            if node.get("additionalProperties") is False:
                for key in value:
                    if key not in properties:
                        child = f"{path}.{key}" if path else key
                        messages.append(ValidationMessage("error", "schema_unknown_field", "unknown field", child))
            for key, child_node in properties.items():
                if key in value:
                    child = f"{path}.{key}" if path else key
                    walk(value[key], child_node, child)
        if isinstance(value, (int, float)):
            if "exclusiveMinimum" in node and not value > node["exclusiveMinimum"]:
                messages.append(ValidationMessage("error", "schema_minimum", f"must be > {node['exclusiveMinimum']}", path))
            if "minimum" in node and not value >= node["minimum"]:
                messages.append(ValidationMessage("error", "schema_minimum", f"must be >= {node['minimum']}", path))

    walk(spec, schema, "")
    return messages


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(value, item) for item in expected)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True
