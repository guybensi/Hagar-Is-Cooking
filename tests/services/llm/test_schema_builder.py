from pydantic import BaseModel

from app.services.llm.schema_builder import build_json_schema_response_format


class _Nested(BaseModel):
    label: str
    optional_note: str | None = None


class _Sample(BaseModel):
    name: str
    tags: list[_Nested]


def test_response_format_has_expected_shape():
    response_format = build_json_schema_response_format(_Sample)

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "_Sample"
    assert response_format["json_schema"]["strict"] is True


def test_top_level_object_forbids_additional_properties_and_requires_all_fields():
    response_format = build_json_schema_response_format(_Sample)
    schema = response_format["json_schema"]["schema"]

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"name", "tags"}


def test_nested_definitions_are_also_made_strict():
    response_format = build_json_schema_response_format(_Sample)
    schema = response_format["json_schema"]["schema"]

    nested_schema = schema["$defs"]["_Nested"]
    assert nested_schema["additionalProperties"] is False
    assert set(nested_schema["required"]) == {"label", "optional_note"}
