"""Tests for FHIR Bundle helper functions."""

import pytest
from fhir.resources.bundle import Bundle
from fhir.resources.condition import Condition
from fhir.resources.medicationstatement import MedicationStatement
from fhir.resources.allergyintolerance import AllergyIntolerance
from fhir.resources.documentreference import DocumentReference

from healthchain.fhir.bundle_helpers import (
    create_bundle,
    add_resource,
    get_resources,
    set_resources,
    get_resource_type,
)


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
