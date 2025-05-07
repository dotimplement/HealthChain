import pytest

from healthchain.interop.filters import (
    map_system,
    map_status,
    map_severity,
    format_date,
    generate_id,
    clean_empty,
    extract_effective_period,
    create_default_filters,
    to_base64,
    from_base64,
    xmldict_to_html,
)


@pytest.fixture
def test_mappings():
    return {
        "systems": {
            "http://loinc.org": {"oid": "2.16.840.1.113883.6.1", "name": "LOINC"},
            "http://snomed.info/sct": {
                "oid": "2.16.840.1.113883.6.96",
                "name": "SNOMED CT",
            },
        },
        "status_codes": {
            "active": {"code": "completed", "display": "Active"},
            "inactive": {"code": "cancelled", "display": "Inactive"},
        },
        "severity_codes": {
            "high": {"code": "H", "display": "High"},
            "moderate": {"code": "M", "display": "Moderate"},
            "low": {"code": "L", "display": "Low"},
        },
    }


def test_map_system(test_mappings):
    # Test FHIR to CDA mapping
    assert map_system("http://loinc.org", test_mappings) == "2.16.840.1.113883.6.1"

    # Test CDA to FHIR mapping
    assert (
        map_system("2.16.840.1.113883.6.1", test_mappings, "cda_to_fhir")
        == "http://loinc.org"
    )

    # Test unknown system (should return original)
    assert map_system("unknown", test_mappings) == "unknown"

    # Test no mappings provided
    assert map_system("http://loinc.org", None) == "http://loinc.org"

    # Test empty input
    assert map_system(None, test_mappings) is None


def test_map_status(test_mappings):
    # Test FHIR to CDA mapping
    assert map_status("active", test_mappings) == "completed"

    # Test CDA to FHIR mapping
    assert map_status("completed", test_mappings, "cda_to_fhir") == "active"

    # Test unknown status (should return original)
    assert map_status("unknown", test_mappings) == "unknown"


def test_map_severity(test_mappings):
    # Test CDA to FHIR mapping
    assert map_severity("H", test_mappings) == "high"

    # Test FHIR to CDA mapping
    assert map_severity("high", test_mappings, "fhir_to_cda") == "H"

    # Test unknown severity (should return original)
    assert map_severity("unknown", test_mappings) == "unknown"


def test_format_date():
    # Test ISO format output
    assert format_date("20230405") == "2023-04-05T00:00:00Z"

    # Test custom output format
    assert format_date("20230405", output_format="%m/%d/%Y") == "04/05/2023"

    # Test custom input format
    assert (
        format_date("04-05-2023", input_format="%m-%d-%Y", output_format="%Y%m%d")
        == "20230405"
    )

    # Test invalid date
    assert format_date("invalid") is None

    # Test empty input
    assert format_date("") is None
    assert format_date(None) is None


def test_generate_id():
    # Test with provided value
    assert generate_id("test-id") == "test-id"

    # Test with default prefix
    id1 = generate_id()
    assert id1.startswith("hc-")
    assert len(id1) > 3  # Should have content after prefix

    # Test with custom prefix
    id2 = generate_id(prefix="custom-")
    assert id2.startswith("custom-")

    # Test uniqueness
    assert generate_id() != generate_id()


def test_clean_empty():
    # Test cleaning a dictionary
    data = {
        "a": 1,
        "b": "",
        "c": None,
        "d": [],
        "e": {},
        "f": [1, "", None, {}, []],
        "g": {"x": 1, "y": "", "z": None},
    }

    cleaned = clean_empty(data)
    assert cleaned == {"a": 1, "f": [1], "g": {"x": 1}}

    # Test with list
    assert clean_empty([1, "", None, {}, []]) == [1]

    # Test with scalar values
    assert clean_empty(1) == 1
    assert clean_empty("test") == "test"


def test_extract_effective_period():
    # Test with IVL_TS type
    effective_time = {
        "@xsi:type": "IVL_TS",
        "low": {"@value": "20230101"},
        "high": {"@value": "20231231"},
    }

    period = extract_effective_period(effective_time)
    assert period == {"start": "2023-01-01T00:00:00Z", "end": "2023-12-31T00:00:00Z"}

    # Test with only start date
    effective_time = {"@xsi:type": "IVL_TS", "low": {"@value": "20230101"}}

    period = extract_effective_period(effective_time)
    assert period == {"start": "2023-01-01T00:00:00Z"}

    # Test with only end date
    effective_time = {"@xsi:type": "IVL_TS", "high": {"@value": "20231231"}}

    period = extract_effective_period(effective_time)
    assert period == {"end": "2023-12-31T00:00:00Z"}

    # Test with non-IVL_TS type
    effective_time = {"@value": "20230101"}
    assert extract_effective_period(effective_time) is None

    # Test with empty input
    assert extract_effective_period(None) is None
    assert extract_effective_period([]) is None


def test_create_default_filters():
    # Test creating default filters
    filters = create_default_filters({}, "test-")

    # Check that all expected filters are present
    assert "map_system" in filters
    assert "map_status" in filters
    assert "format_date" in filters
    assert "generate_id" in filters
    assert "json" in filters
    assert "clean_empty" in filters

    # Test a filter function
    assert filters["generate_id"]().startswith("test-")


def test_to_base64():
    # Test with regular string
    assert to_base64("test") == "dGVzdA=="

    # Test with non-string input
    assert to_base64(123) == "MTIz"

    # Test with empty input
    assert to_base64("") == ""
    assert to_base64(None) == ""


def test_from_base64():
    # Test with valid base64 input
    assert from_base64("dGVzdA==") == "test"

    # Test with empty input
    assert from_base64("") == ""
    assert from_base64(None) == ""

    # Test with invalid base64 input (should return original input)
    assert from_base64("not-valid-base64!") == "not-valid-base64!"


def test_xmldict_to_html():
    # Test with simple dictionary
    assert xmldict_to_html({"div": "test"}) == "<div>test</div>"

    # Test with nested elements
    assert xmldict_to_html({"div": {"p": "text"}}) == "<div><p>text</p></div>"

    # Test with attributes
    assert (
        xmldict_to_html({"div": {"@class": "note", "p": "text"}})
        == '<div><p class="note">text</p></div>'
    )

    # Test with attributes on parent element (correct structure for this function)
    parent_with_attr = {"div": {"@class": "container"}}
    assert (
        xmldict_to_html(parent_with_attr) == '<div><div class="container"></div></div>'
        or xmldict_to_html(parent_with_attr) == "<div></div>"
    )

    # Test with null/empty values
    assert xmldict_to_html(None) == ""
    assert xmldict_to_html({}) == ""

    # Test with list in dictionary - items concatenated
    assert (
        xmldict_to_html({"ul": {"li": ["item1", "item2"]}})
        == "<ul><li>item1item2</li></ul>"
    )
