"""Tests for IPA client exceptions and initialization."""

import pytest
from ipaclient import (
    IPAClient,
    IPAError,
    IPAConnectionError,
    IPAAuthenticationError,
    IPAServerError,
    IPASchemaError,
    IPAValidationError,
)


def test_ipa_error_basic():
    """Test IPAError with message only."""
    error = IPAError("Something went wrong")
    assert str(error) == "Something went wrong"
    assert error.message == "Something went wrong"
    assert error.code == "IPAError"
    assert error.data == {}


def test_ipa_error_with_code():
    """Test IPAError with custom code."""
    error = IPAError("Not found", code="NotFound")
    assert error.code == "NotFound"


def test_ipa_error_with_data():
    """Test IPAError with additional data."""
    error = IPAError("Validation failed", data={"field": "username"})
    assert error.data == {"field": "username"}


def test_ipa_error_to_dict():
    """Test IPAError.to_dict() method."""
    error = IPAError("Test error", code="TestCode", data={"key": "value"})
    result = error.to_dict()
    assert result == {
        "error": {
            "code": "TestCode",
            "message": "Test error",
            "data": {"key": "value"},
        }
    }


def test_ipa_error_subclasses():
    """Test exception subclass hierarchy."""
    connection_error = IPAConnectionError("Connection failed")
    assert isinstance(connection_error, IPAError)
    assert connection_error.code == "IPAConnectionError"

    auth_error = IPAAuthenticationError("Auth failed")
    assert isinstance(auth_error, IPAError)
    assert auth_error.code == "IPAAuthenticationError"

    server_error = IPAServerError("Server error")
    assert isinstance(server_error, IPAError)
    assert server_error.code == "IPAServerError"

    schema_error = IPASchemaError("Schema error")
    assert isinstance(schema_error, IPAError)
    assert schema_error.code == "IPASchemaError"

    validation_error = IPAValidationError("Validation error")
    assert isinstance(validation_error, IPAError)
    assert validation_error.code == "IPAValidationError"


# ============================================================================
# Client Initialization Tests
# ============================================================================


def test_client_init_basic(mock_server):
    """Test basic client initialization."""
    client = IPAClient(mock_server)
    assert client._server == mock_server
    assert client._base_url == f"https://{mock_server}"
    assert client._json_url == f"https://{mock_server}/ipa/json"
    assert client._verify_ssl is True
    assert client._schema is None


def test_client_init_no_ssl_verify(mock_server):
    """Test client initialization with SSL verification disabled."""
    client = IPAClient(mock_server, verify_ssl=False)
    assert client._verify_ssl is False


def test_client_init_url_construction():
    """Test URL construction for various server formats."""
    # Just hostname
    client = IPAClient("ipa.example.com")
    assert client._base_url == "https://ipa.example.com"

    # Hostname with domain
    client = IPAClient("ipa.corp.example.com")
    assert client._base_url == "https://ipa.corp.example.com"

    # IP address
    client = IPAClient("192.168.1.100")
    assert client._base_url == "https://192.168.1.100"
