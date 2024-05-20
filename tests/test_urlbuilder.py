import pytest

from healthchain.utils.urlbuilder import UrlBuilder


# A simple mock for Endpoint objects
class MockEndpoint:
    def __init__(self, path):
        self.path = path


@pytest.fixture
def config():
    return {"host": "example.com", "port": "8080"}


@pytest.fixture
def endpoints():
    return {"service_mount": MockEndpoint("/api/service/{id}")}


def test_https_protocol_if_ssl_keyfile_present(config, endpoints):
    config["ssl_keyfile"] = "path/to/keyfile"
    url = UrlBuilder.build_from_config(config, endpoints, "123")
    assert url.service == "https://example.com:8080/api/service/123"
    assert url.base == "https://example.com:8080"
    assert url.route == "/api/service/123"


def test_http_protocol_if_no_ssl_keyfile(config, endpoints):
    url = UrlBuilder.build_from_config(config, endpoints, "123")
    assert url.service == "http://example.com:8080/api/service/123"
    assert url.base == "http://example.com:8080"
    assert url.route == "/api/service/123"


def test_default_host_and_port_if_not_provided(endpoints):
    config = {}
    url = UrlBuilder.build_from_config(config, endpoints, "123")
    assert url.service == "http://127.0.0.1:8000/api/service/123"
    assert url.base == "http://127.0.0.1:8000"
    assert url.route == "/api/service/123"


def test_raise_error_if_service_mount_missing(config):
    config["ssl_keyfile"] = "path/to/keyfile"
    endpoints = {}  # No service_mount
    with pytest.raises(ValueError):
        UrlBuilder.build_from_config(config, endpoints, "service123")


def test_proper_service_id_formatting(config, endpoints):
    url = UrlBuilder.build_from_config(config, endpoints, "service123")
    assert url.service == "http://example.com:8080/api/service/service123"
    assert url.base == "http://example.com:8080"
    assert url.route == "/api/service/service123"
