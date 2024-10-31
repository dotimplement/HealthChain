from healthchain.pipeline.components.postprocessors import TextPostProcessor
from healthchain.io.containers import Document


def test_text_postprocessor_initialization_and_processing():
    # Test initialization without lookup
    processor = TextPostProcessor()
    assert processor.entity_lookup == {}

    # Test initialization with lookup
    processor = TextPostProcessor(postcoordination_lookup={"a": "b"})
    assert processor.entity_lookup == {"a": "b"}

    # Test processing with empty lookup
    doc = Document(data="")
    doc.nlp.entities = [
        {"text": "high blood pressure"},
        {"text": "fever"},
        {"text": "heart attack"},
    ]
    processed_doc = processor(doc)
    assert [entity["text"] for entity in processed_doc.get_entities()] == [
        "high blood pressure",
        "fever",
        "heart attack",
    ]


def test_text_postprocessor_with_entities(sample_lookup):
    processor = TextPostProcessor(postcoordination_lookup=sample_lookup)

    # Test with matching entities
    doc = Document(data="")
    doc.nlp.entities = [
        {"text": "high blood pressure"},
        {"text": "fever"},
        {"text": "heart attack"},
    ]
    processed_doc = processor(doc)
    assert [entity["text"] for entity in processed_doc.get_entities()] == [
        "hypertension",
        "fever",
        "myocardial infarction",
    ]

    # Test with mixed entities
    doc = Document(data="")
    doc.nlp.entities = [
        {"text": "high blood pressure"},
        {"text": "cough"},
        {"text": "heart attack"},
        {"text": "fever"},
    ]
    processed_doc = processor(doc)
    assert [entity["text"] for entity in processed_doc.get_entities()] == [
        "hypertension",
        "cough",
        "myocardial infarction",
        "fever",
    ]


def test_text_postprocessor_edge_cases(sample_lookup):
    processor = TextPostProcessor(postcoordination_lookup=sample_lookup)

    # Test with document without entities
    doc = Document(data="This is a test document")
    processed_doc = processor(doc)
    assert processed_doc == doc

    # Test with empty entities list
    doc = Document(data="")
    doc.entities = []
    processed_doc = processor(doc)
    assert processed_doc.get_entities() == []

    # Test with document having no 'entities' attribute
    doc = Document(data="Document without entities attribute")
    processed_doc = processor(doc)
    assert processed_doc == doc
