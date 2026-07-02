from typing import Any

from pydantic import BaseModel


def _enforce_strict(schema: dict[str, Any]) -> None:
    """Recursively enforce Groq/OpenAI strict json_schema rules on a Pydantic JSON schema.

    Strict mode requires every object to set `additionalProperties: false` and list *every*
    property (including optional/nullable ones) in `required` -- optionality is instead
    expressed via a `null` member of the field's type/anyOf.
    """
    if "properties" in schema:
        schema["additionalProperties"] = False
        properties = schema["properties"]
        schema["required"] = list(properties.keys())
        for prop_schema in properties.values():
            _enforce_strict(prop_schema)

    if "items" in schema:
        _enforce_strict(schema["items"])

    for key in ("anyOf", "oneOf", "allOf"):
        for sub_schema in schema.get(key, []):
            _enforce_strict(sub_schema)

    for def_schema in schema.get("$defs", {}).values():
        _enforce_strict(def_schema)


def build_json_schema_response_format(model: type[BaseModel]) -> dict[str, Any]:
    """Build a Groq `response_format` dict (json_schema strict mode) from a Pydantic model."""
    schema = model.model_json_schema()
    _enforce_strict(schema)

    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "schema": schema,
            "strict": True,
        },
    }
