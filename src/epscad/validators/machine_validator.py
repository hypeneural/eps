from __future__ import annotations

from typing import Any

from epscad.loader import ROOT, load_json, load_machine_profile
from epscad.schema import ValidationMessage


def validate_machine_profile_exists(spec: dict[str, Any]) -> list[ValidationMessage]:
    profile = str(spec.get("machine", {}).get("profile", ""))
    if not profile:
        return [ValidationMessage("error", "machine_profile_missing", "machine.profile is required", "machine.profile")]
    try:
        machine_profile = load_machine_profile(profile)
    except FileNotFoundError as exc:
        return [ValidationMessage("error", "machine_profile_not_found", str(exc), "machine.profile")]
    return validate_machine_profile_schema(machine_profile)


def validate_machine_profile_schema(profile: dict[str, Any]) -> list[ValidationMessage]:
    schema = load_json(ROOT / "schemas" / "machine_profile_hotwire.schema.json")
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return _fallback_validate_machine_profile(profile, schema)

    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(profile), key=lambda item: list(item.absolute_path))
    messages: list[ValidationMessage] = []
    for error in errors:
        path = ".".join(str(part) for part in error.absolute_path)
        code = "machine_profile_schema_unknown_field" if error.validator == "additionalProperties" else "machine_profile_schema_error"
        messages.append(ValidationMessage("error", code, error.message, path))
    return messages


def _fallback_validate_machine_profile(profile: dict[str, Any], schema: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []

    def walk(value: Any, node: dict[str, Any], path: str) -> None:
        if "const" in node and value != node["const"]:
            messages.append(ValidationMessage("error", "machine_profile_schema_const", f"expected {node['const']!r}", path))
        if "enum" in node and value not in node["enum"]:
            messages.append(ValidationMessage("error", "machine_profile_schema_enum", f"{value!r} not in {node['enum']}", path))
        expected_type = node.get("type")
        if expected_type and not _matches_type(value, expected_type):
            messages.append(ValidationMessage("error", "machine_profile_schema_type", f"expected type {expected_type}", path))
            return
        if isinstance(value, dict):
            required = node.get("required", [])
            for key in required:
                if key not in value:
                    child = f"{path}.{key}" if path else key
                    messages.append(ValidationMessage("error", "machine_profile_schema_required", "missing required field", child))
            properties = node.get("properties", {})
            if node.get("additionalProperties") is False:
                for key in value:
                    if key not in properties:
                        child = f"{path}.{key}" if path else key
                        messages.append(ValidationMessage("error", "machine_profile_schema_unknown_field", "unknown field", child))
            for key, child_node in properties.items():
                if key in value:
                    child = f"{path}.{key}" if path else key
                    walk(value[key], child_node, child)

    walk(profile, schema, "")
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
