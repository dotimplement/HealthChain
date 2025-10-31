"""Tests for bundle resource counting functionality."""

from healthchain.fhir import (
    create_bundle,
    add_resource,
    create_condition,
    create_medication_statement,
    create_allergy_intolerance,
    count_resources,
)


def test_count_resources_with_empty_bundle(empty_bundle):
    """count_resources returns empty dict for empty bundle."""
    counts = count_resources(empty_bundle)
    assert counts == {}


def test_count_resources_with_single_resource_type(empty_bundle):
    """count_resources counts single resource type correctly."""
    add_resource(empty_bundle, create_condition("Patient/1", "123", "Test"))
    add_resource(empty_bundle, create_condition("Patient/1", "456", "Test 2"))

    counts = count_resources(empty_bundle)
    assert counts == {"Condition": 2}


def test_count_resources_with_mixed_resource_types(empty_bundle):
    """count_resources counts multiple resource types correctly."""
    add_resource(empty_bundle, create_condition("Patient/1", "123", "Test"))
    add_resource(empty_bundle, create_condition("Patient/1", "456", "Test 2"))
    add_resource(empty_bundle, create_medication_statement("Patient/1", "789", "Med"))
    add_resource(
        empty_bundle, create_allergy_intolerance("Patient/1", "999", "Allergy")
    )

    counts = count_resources(empty_bundle)
    assert counts == {
        "Condition": 2,
        "MedicationStatement": 1,
        "AllergyIntolerance": 1,
    }


def test_count_resources_with_none_bundle():
    """count_resources handles None bundle gracefully."""
    counts = count_resources(None)
    assert counts == {}


def test_count_resources_with_bundle_no_entry():
    """count_resources handles bundle with None entry."""
    bundle = create_bundle()
    bundle.entry = None

    counts = count_resources(bundle)
    assert counts == {}
