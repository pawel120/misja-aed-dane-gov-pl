"""Flaga wykazu AED w automatycznym imporcie (harvester XML i CKAN), na wzór containsProtectedData (DGA)."""

from pathlib import Path

import pytest
import xmlschema
from marshmallow import ValidationError

from mcod.harvester.serializers import ResourceSchema, XMLResourceSchema
from mcod.harvester.utils import get_xml_as_dict, get_xml_schema_path, validate_xml

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLE_1_13 = REPO_ROOT / "data" / "test_samples" / "harvester" / "import_example1.13.xml"
EXAMPLE_1_14 = REPO_ROOT / "data" / "test_samples" / "harvester" / "import_example1.14.xml"


def resources_of(data):
    return data["dataset"][0]["resources"]["resource"]


def test_schema_1_14_is_registered():
    assert Path(get_xml_schema_path("1.14")).name == "xml_import_otwarte_dane_1_14.xsd"


def test_example_1_14_is_valid_and_carries_aed_flag():
    assert validate_xml(EXAMPLE_1_14) == "1.14"
    resources = resources_of(get_xml_as_dict(str(EXAMPLE_1_14), "1.14"))
    assert [resource.get("containsAedList") for resource in resources[:2]] == [None, True]


def test_older_versions_are_unchanged():
    assert validate_xml(EXAMPLE_1_13) == "1.13"


def test_aed_flag_is_not_allowed_in_1_13(tmp_path):
    content = EXAMPLE_1_14.read_text(encoding="utf-8").replace("harvester:1.14", "harvester:1.13")
    path = tmp_path / "aed_in_1_13.xml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(xmlschema.XMLSchemaValidationError):
        validate_xml(path)


def test_xml_resource_schema_maps_flag_to_model_field():
    field = XMLResourceSchema().fields["contains_aed_list"]
    assert field.data_key == "containsAedList"
    assert field.missing is False
    assert field.deserialize(True) is True


@pytest.mark.parametrize("value, expected", [(True, True), ("false", False)])
def test_ckan_resource_schema_reads_flag(value, expected):
    assert ResourceSchema().fields["contains_aed_list"].deserialize(value) is expected
    assert "contains_aed_list" in ResourceSchema.Meta.fields


def test_ckan_null_flag_is_a_validation_error_not_a_database_error():
    with pytest.raises(ValidationError):
        ResourceSchema().fields["contains_aed_list"].deserialize(None)
