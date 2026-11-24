from __future__ import annotations

from typing import Any

from epscad.schema import ValidationMessage
from epscad.validators.hotwire_validator import validate_hotwire
from epscad.validators.machine_validator import validate_machine_profile_exists
from epscad.validators.production_gate import validate_production_gates
from epscad.validators.schema_validator import validate_schema
from epscad.validators.tp40_validator import validate_tp40


def validate_project(spec: dict[str, Any]) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    messages.extend(validate_schema(spec))
    messages.extend(validate_machine_profile_exists(spec))
    messages.extend(validate_production_gates(spec))
    messages.extend(_validate_process_specific(spec))
    messages.extend(validate_tp40(spec))
    return messages


def _validate_process_specific(spec: dict[str, Any]) -> list[ValidationMessage]:
    process_type = str(spec.get("machine", {}).get("process_type", ""))
    if process_type == "hotwire_2d":
        return validate_hotwire(spec)
    return [ValidationMessage("error", "process_type_unsupported", f"Unsupported process_type={process_type}", "machine.process_type")]
