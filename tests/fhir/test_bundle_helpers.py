"""Tests for FHIR Bundle helper functions."""

import pytest
from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.documentreference import DocumentReference

from healthchain.fhir.bundlehelpers import (
    create_bundle,
    add_resource,
    get_resources,
    set_resources,
    get_resource_type,
    extract_resources,
)
from healthchain.fhir import merge_bundles, create_condition


def test_create_bundle():
    """Test creating an empty bundle."""
    bundle = create_bundle()
    assert isinstance(bundle, Bundle)
    assert bundle.type == "collection"
    assert bundle.entry == []

    # Test with different type
    bundle = create_bundle(bundle_type="transaction")
    assert bundle.type == "transaction"


def test_add_resource(empty_bundle, test_condition):
    """Test adding a resource to a bundle."""
    add_resource(empty_bundle, test_condition)
    assert len(empty_bundle.entry) == 1
    assert isinstance(empty_bundle.entry[0].resource, Condition)

    # Test with full URL
    add_resource(empty_bundle, test_condition, full_url="http://test.com/Condition/123")
    assert len(empty_bundle.entry) == 2
    assert empty_bundle.entry[1].fullUrl == "http://test.com/Condition/123"


def test_get_resource_type():
    """Test getting resource type from string or class."""
    # Test with string
    assert get_resource_type("Condition") == Condition
    assert get_resource_type("MedicationStatement") == MedicationStatement
    assert get_resource_type("AllergyIntolerance") == AllergyIntolerance
    assert get_resource_type("DocumentReference") == DocumentReference
    # Test with class
    assert get_resource_type(Condition) == Condition

    # Test invalid type
    with pytest.raises(ValueError, match="Could not import resource type"):
        get_resource_type("InvalidType")

    # Test invalid input type
    with pytest.raises(
        ValueError, match="Resource type must be a string or Resource class"
    ):
        get_resource_type(123)


def test_get_resources(empty_bundle, test_condition, test_medication, test_allergy):
    """Test getting resources by type."""
    # Add mixed resources
    add_resource(empty_bundle, test_condition)
    add_resource(empty_bundle, test_medication)
    add_resource(empty_bundle, test_allergy)
    add_resource(empty_bundle, test_condition)  # Add another condition

    # Test getting by string type
    conditions = get_resources(empty_bundle, "Condition")
    assert len(conditions) == 2
    assert all(isinstance(c, Condition) for c in conditions)

    # Test getting by class type
    medications = get_resources(empty_bundle, MedicationStatement)
    assert len(medications) == 1
    assert isinstance(medications[0], MedicationStatement)


def test_set_resources_append(empty_bundle, test_condition, test_medication):
    """Test setting resources with append mode."""
    # Add initial condition
    add_resource(empty_bundle, test_condition)
    assert len(get_resources(empty_bundle, "Condition")) == 1

    # Add more conditions without replace
    set_resources(empty_bundle, [test_condition], "Condition", replace=False)
    assert len(get_resources(empty_bundle, "Condition")) == 2

    # Add medication (shouldn't affect conditions)
    set_resources(empty_bundle, [test_medication], "MedicationStatement")
    assert len(get_resources(empty_bundle, "Condition")) == 2
    assert len(get_resources(empty_bundle, "MedicationStatement")) == 1


def test_set_resources_replace(empty_bundle, test_condition, test_medication):
    """Test setting resources with replace mode."""
    # Add initial resources
    add_resource(empty_bundle, test_condition)
    add_resource(empty_bundle, test_condition)
    assert len(get_resources(empty_bundle, "Condition")) == 2

    # Replace conditions
    set_resources(empty_bundle, [test_condition], "Condition", replace=True)
    assert len(get_resources(empty_bundle, "Condition")) == 1

    # Add medication (shouldn't affect conditions)
    set_resources(empty_bundle, [test_medication], "MedicationStatement", replace=True)
    assert len(get_resources(empty_bundle, "Condition")) == 1
    assert len(get_resources(empty_bundle, "MedicationStatement")) == 1


def test_set_resources_type_validation(empty_bundle, test_condition):
    """Test type validation in set_resources."""
    # Try to add condition as medication
    with pytest.raises(
        ValueError, match="Resource must be of type MedicationStatement"
    ):
        set_resources(empty_bundle, [test_condition], "MedicationStatement")


def test_merge_bundles_basic_and_type():
    """Merging combines entries and sets bundle type to collection by default."""
    b1 = create_bundle("searchset")
    add_resource(b1, create_condition(subject="Patient/123", code="E11.9"))
    add_resource(b1, create_condition(subject="Patient/123", code="I10"))

    b2 = create_bundle("searchset")
    add_resource(b2, create_condition(subject="Patient/123", code="J44.9"))

    merged = merge_bundles([b1, b2])
    assert merged.entry is not None and len(merged.entry) == 3
    assert merged.type == "collection"


def test_merge_bundles_deduplication_toggle():
    """Deduplication removes dups when True, keeps when False."""
    c1 = create_condition(subject="Patient/123", code="E11.9")
    c1.id = "cond-1"
    c1_dup = create_condition(subject="Patient/123", code="E11.9")
    c1_dup.id = "cond-1"

    b1 = create_bundle("searchset")
    add_resource(b1, c1)
    b2 = create_bundle("searchset")
    add_resource(b2, c1_dup)

    merged_dedupe = merge_bundles([b1, b2], deduplicate=True)
    assert merged_dedupe.entry is not None and len(merged_dedupe.entry) == 1

    merged_all = merge_bundles([b1, b2], deduplicate=False)
    assert merged_all.entry is not None and len(merged_all.entry) == 2


def test_merge_bundles_preserves_full_url_and_handles_empty_none():
    """Preserves fullUrl and handles empty/None bundles."""
    b1 = create_bundle("searchset")
    cond = create_condition(subject="Patient/123", code="E11.9")
    add_resource(b1, cond, full_url="http://example.com/Condition/123")

    b2 = create_bundle("searchset")  # empty

    merged = merge_bundles([b1, b2, None])
    assert merged.entry is not None and len(merged.entry) == 1
    assert merged.entry[0].fullUrl == "http://example.com/Condition/123"


def test_merge_bundles_customizations():
    """Supports custom bundle_type and custom dedupe_key semantics."""
    # custom bundle_type
    b = create_bundle("searchset")
    add_resource(b, create_condition(subject="Patient/123", code="E11.9"))
    merged_txn = merge_bundles([b], bundle_type="transaction")
    assert merged_txn.type == "transaction"

    # custom dedupe_key (keep both because ids differ)
    c1 = create_condition(subject="Patient/123", code="E11.9")
    c1.id = "id-1"
    c2 = create_condition(subject="Patient/123", code="E11.9")
    c2.id = "id-2"
    b1 = create_bundle("searchset")
    add_resource(b1, c1)
    b2 = create_bundle("searchset")
    add_resource(b2, c2)
    merged_custom_key = merge_bundles([b1, b2], deduplicate=True, dedupe_key="id")
    assert merged_custom_key.entry is not None and len(merged_custom_key.entry) == 2


def test_extract_resources_removes_and_returns():
    """extract_resources removes resources of a type and returns them."""
    b = create_bundle()
    c1 = create_condition(subject="Patient/1", code="E11.9")
    c2 = create_condition(subject="Patient/1", code="I10")
    add_resource(b, c1)
    add_resource(b, c2)
    extracted = extract_resources(b, "Condition")
    assert len(extracted) == 2
    assert b.entry == []


def test_merge_bundles_dedupe_missing_key_keeps_all():
    """Resources missing dedupe_key should not be collapsed when deduplicate=True."""
    b1 = create_bundle("searchset")
    b2 = create_bundle("searchset")
    c1 = create_condition(subject="Patient/1", code="E11.9")
    c1.id = None
    c2 = create_condition(subject="Patient/1", code="E11.9")
    c2.id = None
    add_resource(b1, c1)
    add_resource(b2, c2)
    merged = merge_bundles([b1, b2], deduplicate=True, dedupe_key="id")
    assert merged.entry is not None and len(merged.entry) == 2
