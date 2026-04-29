from healthchain.utils.idgenerator import generate_id, HC_PREFIX, DEFAULT_PATIENT_REF


def test_hc_prefix_constant():
    assert HC_PREFIX == "hc-"


def test_default_patient_ref_constant():
    assert DEFAULT_PATIENT_REF == "Patient/123"


def test_generate_id_default_prefix():
    result = generate_id()
    assert result.startswith("hc-")


def test_generate_id_custom_prefix():
    result = generate_id("doc-")
    assert result.startswith("doc-")


def test_generate_id_unique():
    assert generate_id() != generate_id()


def test_generate_id_contains_uuid():
    result = generate_id()
    # Strip prefix and verify remaining string is a valid UUID (32 hex + 4 dashes)
    uuid_part = result[len(HC_PREFIX):]
    assert len(uuid_part) == 36
    assert uuid_part.count("-") == 4
