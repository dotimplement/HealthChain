import pytest
from unittest.mock import Mock, patch
from healthchain.interop.parsers.cda import CDAParser
from healthchain.interop.config_manager import InteropConfigManager


@pytest.fixture
def mock_config():
    config = Mock(spec=InteropConfigManager)
    config.get_cda_section_configs.return_value = {}
    config.get_config_value.return_value = None
    return config


@pytest.fixture
def parser(mock_config):
    return CDAParser(mock_config)


@pytest.fixture
def sample_xml(tmp_path):
    f = tmp_path / "test.xml"
    f.write_text("<root><element>test</element></root>", encoding="utf-8")
    return f


# --- from_file ---

def test_from_file_reads_and_parses(parser, sample_xml):
    """from_file should read the file and call from_string."""
    with patch.object(parser, "from_string", return_value={"ok": True}) as mock:
        result = parser.from_file(str(sample_xml))
        mock.assert_called_once()
        assert result == {"ok": True}


def test_from_file_raises_if_not_found(parser):
    """from_file should raise FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        parser.from_file("/nonexistent/path/file.xml")


# --- from_directory ---

def test_from_directory_yields_results(parser, tmp_path):
    """from_directory should yield parsed results for each matching file."""
    for i in range(3):
        (tmp_path / f"doc{i}.xml").write_text(f"<root>{i}</root>", encoding="utf-8")

    with patch.object(parser, "from_string", return_value={"ok": True}):
        results = list(parser.from_directory(str(tmp_path), pattern="*.xml"))
        assert len(results) == 3


def test_from_directory_empty_yields_nothing(parser, tmp_path):
    """from_directory should yield nothing if no files match the pattern."""
    results = list(parser.from_directory(str(tmp_path), pattern="*.xml"))
    assert results == []


# --- from_bytes ---

def test_from_bytes_decodes_and_parses(parser):
    """from_bytes should decode bytes and call from_string."""
    data = b"<root>test</root>"
    with patch.object(parser, "from_string", return_value={"ok": True}) as mock:
        result = parser.from_bytes(data)
        mock.assert_called_once_with("<root>test</root>")
        assert result == {"ok": True}


def test_from_bytes_raises_if_empty(parser):
    """from_bytes should raise ValueError for empty bytes."""
    with pytest.raises(ValueError, match="empty"):
        parser.from_bytes(b"")


# --- from_url ---

def test_from_url_fetches_and_parses(parser):
    """from_url should fetch content and call from_string."""
    mock_response = Mock()
    mock_response.text = "<root>test</root>"
    mock_response.raise_for_status = Mock()

    with patch("httpx.get", return_value=mock_response):
        with patch.object(parser, "from_string", return_value={"ok": True}) as mock:
            result = parser.from_url("http://example.com/test.xml")
            mock.assert_called_once_with("<root>test</root>")
            assert result == {"ok": True}


def test_from_url_raises_on_http_error(parser):
    """from_url should raise ValueError on HTTP errors."""
    import httpx
    mock_response = Mock()
    mock_response.status_code = 404
    with patch("httpx.get", side_effect=httpx.HTTPStatusError(
        "404", request=Mock(), response=mock_response
    )):
        with pytest.raises(ValueError, match="HTTP error"):
            parser.from_url("http://example.com/missing.xml")