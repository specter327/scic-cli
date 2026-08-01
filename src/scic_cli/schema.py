from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


def _get(schema: Mapping[str, Any], name: str, default: Any = None) -> Any:
    """Read both DataValue's canonical keys and normalized SCIC keys."""
    if name in schema:
        return schema[name]
    return schema.get(name.upper(), default)


def _type_name(value: Any) -> str:
    if isinstance(value, type):
        return value.__name__
    if isinstance(value, Mapping):
        return str(value.get("__class__") or value.get("name") or value)
    if value is None:
        return "unknown"
    return str(value)


def _unwrap_schema(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    content = value.get("content")
    if isinstance(content, Mapping):
        return content
    if "DATA_TYPE" in value or "data_type" in value:
        return value
    return None


@dataclass(frozen=True, slots=True)
class SchemaDescription:
    """Presentation-friendly view of a serialized DataValue schema."""

    name: str
    data_type: str
    description: str
    characteristics: tuple[str, ...]

    @classmethod
    def from_dict(
        cls,
        schema: Mapping[str, Any],
        *,
        fallback_name: str,
    ) -> "SchemaDescription":
        name = str(_get(schema, "name") or fallback_name)
        data_type = _type_name(_get(schema, "data_type") or _get(schema, "type"))
        description = str(_get(schema, "description") or "")
        characteristics = cls._characteristics(schema)
        return cls(name, data_type, description, tuple(characteristics))

    @classmethod
    def _characteristics(cls, schema: Mapping[str, Any]) -> list[str]:
        result: list[str] = []

        cls._append_range(
            result,
            "Length",
            _get(schema, "minimum_length"),
            _get(schema, "maximum_length"),
        )
        cls._append_range(
            result,
            "Value",
            _get(schema, "minimum_size"),
            _get(schema, "maximum_size"),
        )

        expression = _get(schema, "regular_expression")
        if expression:
            result.append(f"Pattern: {expression}")

        validation_mode = _get(schema, "validation_mode")
        if validation_mode and validation_mode != "any":
            mode = getattr(validation_mode, "value", validation_mode)
            result.append(f"Validation: {mode}")

        possible_values = _get(schema, "possible_values")
        if possible_values not in (None, [], (), {}):
            result.extend(cls._describe_possible_values(possible_values))

        return result

    @staticmethod
    def _append_range(
        result: list[str],
        label: str,
        minimum: Any,
        maximum: Any,
    ) -> None:
        if minimum is not None and maximum is not None:
            result.append(f"{label}: {minimum}..{maximum}")
        elif minimum is not None:
            result.append(f"{label}: >= {minimum}")
        elif maximum is not None:
            result.append(f"{label}: <= {maximum}")

    @classmethod
    def _describe_possible_values(cls, values: Any) -> list[str]:
        if isinstance(values, Mapping):
            return [f"Schema: {json.dumps(values, ensure_ascii=False, default=str)}"]

        if not isinstance(values, (list, tuple, set, frozenset)):
            return [f"Allowed: {values}"]

        nested: list[str] = []
        literals: list[str] = []
        for index, value in enumerate(values):
            schema = _unwrap_schema(value)
            if schema is None:
                if isinstance(value, Mapping) and "__class__" in value:
                    literals.append(str(value["__class__"]))
                else:
                    literals.append(str(value))
                continue

            item = cls.from_dict(schema, fallback_name=f"item_{index}")
            summary = f"[{index}] {item.name}: {item.data_type}"
            if item.description:
                summary += f" — {item.description}"
            if item.characteristics:
                summary += f" ({'; '.join(item.characteristics)})"
            nested.append(summary)

        if literals:
            nested.insert(0, f"Allowed: {', '.join(literals)}")
        return nested


def describe_contract(
    schemas: Any,
    *,
    item_label: str,
) -> tuple[SchemaDescription, ...]:
    if not isinstance(schemas, (list, tuple)):
        return ()

    result: list[SchemaDescription] = []
    for index, raw_schema in enumerate(schemas):
        schema = _unwrap_schema(raw_schema)
        if schema is None:
            schema = {"data_type": type(raw_schema).__name__, "value": raw_schema}
        result.append(
            SchemaDescription.from_dict(
                schema,
                fallback_name=f"{item_label}_{index}",
            )
        )
    return tuple(result)
