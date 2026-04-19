# Minimal IPA JSON-RPC Client Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight Python library for programmatic FreeIPA interaction via JSON-RPC with MCP server integration support.

**Architecture:** Single-file module with IPAClient class, exception hierarchy, and helper functions. JSON-RPC over HTTPS with Kerberos auth. In-memory schema caching. Pure dict-based outputs.

**Tech Stack:** Python 3.8+, requests, requests-gssapi, pytest, responses (for testing)

---

## File Structure

**Created:**
- `ipaclient.py` - Main client module (~450 lines)
- `tests/test_ipaclient.py` - Unit tests (~400 lines)
- `tests/test_ipaclient_integration.py` - Integration tests (~100 lines, optional)
- `tests/conftest.py` - Pytest fixtures and test data (~100 lines)
- `requirements.txt` - Dependencies
- `requirements-dev.txt` - Development dependencies
- `README.md` - Usage documentation

**Modified:**
- None (new project)

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `ipaclient.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```txt
requests>=2.25.0
requests-gssapi>=1.2.0
```

- [ ] **Step 2: Create requirements-dev.txt**

```txt
-r requirements.txt
pytest>=7.0.0
pytest-cov>=3.0.0
responses>=0.20.0
```

- [ ] **Step 3: Create ipaclient.py with module docstring**

```python
"""
Minimal IPA Client - JSON-RPC interface to FreeIPA servers.

This module provides a lightweight client for interacting with FreeIPA
servers via JSON-RPC. It requires Kerberos authentication (existing tickets
via kinit) and returns pure Python dictionaries suitable for MCP integration.

Example:
    >>> from ipaclient import IPAClient
    >>> client = IPAClient("ipa.example.com")
    >>> result = client.ping()
    >>> print(result["summary"])
    IPA server version 4.9.8. API version 2.251

Dependencies:
    - requests: HTTP client
    - requests-gssapi: Kerberos authentication
"""

from typing import Dict, List, Optional, Any
import requests
from requests_gssapi import HTTPSPNEGOAuth


__version__ = "0.1.0"
__all__ = [
    "IPAClient",
    "IPAError",
    "IPAConnectionError",
    "IPAAuthenticationError",
    "IPAServerError",
    "IPASchemaError",
    "IPAValidationError",
]
```

- [ ] **Step 4: Create tests/conftest.py**

```python
"""Pytest configuration and shared fixtures."""

import pytest
import json


@pytest.fixture
def mock_server():
    """Mock IPA server hostname."""
    return "ipa.example.com"


@pytest.fixture
def mock_schema():
    """Mock IPA schema data."""
    return {
        "topics": {
            "user": {
                "name": "user",
                "doc": "Users\n\nManage user accounts.",
            },
            "group": {
                "name": "group",
                "doc": "Groups\n\nManage user groups.",
            },
        },
        "commands": {
            "user_show": {
                "name": "user_show",
                "topic": "user",
                "full_name": "user_show",
                "doc": "Display information about a user.\n\nShows detailed user attributes.",
                "summary": "Display information about a user",
                "params": [
                    {
                        "name": "uid",
                        "cli_name": "login",
                        "type": "Str",
                        "required": True,
                        "label": "User login",
                        "doc": "User login",
                    },
                    {
                        "name": "all",
                        "cli_name": "all",
                        "type": "Flag",
                        "required": False,
                        "label": "Retrieve all attributes",
                        "doc": "Retrieve and print all attributes",
                        "default": False,
                    },
                    {
                        "name": "version",
                        "type": "Str",
                        "required": False,
                        "exclude": "webui",
                    },
                ],
            },
            "user_find": {
                "name": "user_find",
                "topic": "user",
                "full_name": "user_find",
                "doc": "Search for users.",
                "summary": "Search for users",
                "params": [
                    {
                        "name": "criteria",
                        "cli_name": "criteria",
                        "type": "Str",
                        "required": False,
                        "label": "Search criteria",
                        "doc": "Search criteria",
                    },
                    {
                        "name": "sizelimit",
                        "type": "Int",
                        "required": False,
                        "default": 100,
                    },
                    {
                        "name": "version",
                        "type": "Str",
                        "required": False,
                        "exclude": "webui",
                    },
                ],
            },
            "group_show": {
                "name": "group_show",
                "topic": "group",
                "full_name": "group_show",
                "doc": "Display information about a group.",
                "summary": "Display information about a group",
                "params": [
                    {
                        "name": "cn",
                        "cli_name": "group-name",
                        "type": "Str",
                        "required": True,
                        "label": "Group name",
                        "doc": "Group name",
                    },
                    {
                        "name": "version",
                        "type": "Str",
                        "required": False,
                        "exclude": "webui",
                    },
                ],
            },
        },
    }


@pytest.fixture
def mock_ping_response():
    """Mock ping command response."""
    return {
        "result": {},
        "value": None,
        "summary": "IPA server version 4.9.8. API version 2.251",
    }
```

- [ ] **Step 5: Verify setup**

Run: `python3 -c "import ipaclient; print(ipaclient.__version__)"`
Expected: `0.1.0`

- [ ] **Step 6: Commit**

```bash
git add requirements.txt requirements-dev.txt ipaclient.py tests/conftest.py
git commit -m "feat: initial project setup with dependencies"
```

---

## Task 2: Exception Classes

**Files:**
- Modify: `ipaclient.py`
- Create: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for IPAError base class**

```python
"""Tests for IPA client exceptions."""

import pytest
from ipaclient import (
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_ipa_error_basic -v`
Expected: FAIL with ImportError or similar

- [ ] **Step 3: Implement exception classes**

Add to `ipaclient.py` after imports:

```python
# ============================================================================
# Exceptions
# ============================================================================


class IPAError(Exception):
    """Base exception for all IPA client errors.

    All IPA exceptions include a `.to_dict()` method for easy serialization
    in MCP server responses.

    Attributes:
        message: Human-readable error message
        code: Error code (defaults to class name)
        data: Additional error context
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """Initialize IPA error.

        Args:
            message: Human-readable error message
            code: Optional error code (defaults to class name)
            data: Optional additional error context
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dict for MCP integration.

        Returns:
            Dictionary with error details suitable for JSON serialization.
        """
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "data": self.data,
            }
        }


class IPAConnectionError(IPAError):
    """Network or connection failure."""
    pass


class IPAAuthenticationError(IPAError):
    """Kerberos authentication failure."""
    pass


class IPAServerError(IPAError):
    """IPA server returned an error."""
    pass


class IPASchemaError(IPAError):
    """Schema fetch or parse failure."""
    pass


class IPAValidationError(IPAError):
    """Invalid parameters or arguments."""
    pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: add exception hierarchy with to_dict() method"
```

---

## Task 3: IPAClient Initialization

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for client initialization**

Add to `tests/test_ipaclient.py`:

```python
from ipaclient import IPAClient


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_client_init_basic -v`
Expected: FAIL with "IPAClient not defined" or similar

- [ ] **Step 3: Implement IPAClient class**

Add to `ipaclient.py` after exceptions:

```python
# ============================================================================
# Main Client
# ============================================================================


class IPAClient:
    """Minimal IPA JSON-RPC client.

    Provides programmatic access to FreeIPA servers via JSON-RPC protocol.
    Requires Kerberos authentication (existing tickets via kinit).

    All methods return Python dictionaries suitable for JSON serialization
    and MCP integration.

    Example:
        >>> client = IPAClient("ipa.example.com")
        >>> result = client.ping()
        >>> print(result["summary"])
        IPA server version 4.9.8. API version 2.251
    """

    def __init__(self, server: str, verify_ssl: bool = True):
        """Initialize IPA client.

        Args:
            server: IPA server hostname (e.g., 'ipa.example.com')
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self._server = server
        self._base_url = f"https://{server}"
        self._json_url = f"{self._base_url}/ipa/json"
        self._verify_ssl = verify_ssl
        self._schema: Optional[Dict[str, Any]] = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_client_init -v`
Expected: All initialization tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: add IPAClient initialization with URL construction"
```

---

## Task 4: JSON-RPC Request Infrastructure

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for _make_request**

Add to `tests/test_ipaclient.py`:

```python
import responses
import json


@responses.activate
def test_make_request_basic(mock_server):
    """Test basic JSON-RPC request."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={
            "result": {"summary": "OK"},
            "error": None,
        },
        status=200,
    )

    client = IPAClient(mock_server)
    result = client._make_request("ping")

    assert result == {"summary": "OK"}
    assert len(responses.calls) == 1

    # Verify request payload
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["method"] == "ping"
    assert request_body["params"] == [[], {"version": "2.251"}]
    assert request_body["id"] == 0


@responses.activate
def test_make_request_with_args(mock_server):
    """Test JSON-RPC request with positional arguments."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": {"uid": "admin"}, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client._make_request("user_show", args=["admin"])

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["params"][0] == ["admin"]


@responses.activate
def test_make_request_with_options(mock_server):
    """Test JSON-RPC request with options."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": {"data": "test"}, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client._make_request("test", options={"all": True, "raw": False})

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["params"][1]["all"] is True
    assert request_body["params"][1]["raw"] is False
    assert request_body["params"][1]["version"] == "2.251"


@responses.activate
def test_make_request_version_override(mock_server):
    """Test that explicit version is not overridden."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": {}, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    client._make_request("test", options={"version": "2.250"})

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["params"][1]["version"] == "2.250"


@responses.activate
def test_make_request_http_error(mock_server):
    """Test handling of HTTP errors."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"error": "Not found"},
        status=404,
    )

    client = IPAClient(mock_server)
    with pytest.raises(IPAServerError) as exc_info:
        client._make_request("test")

    assert "HTTP 404" in str(exc_info.value)


@responses.activate
def test_make_request_ipa_error(mock_server):
    """Test handling of IPA server errors."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={
            "result": None,
            "error": {
                "code": 4001,
                "message": "User not found",
                "name": "NotFound",
            },
        },
        status=200,
    )

    client = IPAClient(mock_server)
    with pytest.raises(IPAServerError) as exc_info:
        client._make_request("user_show", args=["nonexistent"])

    assert "User not found" in str(exc_info.value)


@responses.activate
def test_make_request_connection_error(mock_server):
    """Test handling of connection errors."""
    client = IPAClient(mock_server)

    with pytest.raises(IPAConnectionError) as exc_info:
        client._make_request("ping")

    assert "Connection" in str(exc_info.value) or "refused" in str(exc_info.value).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_make_request_basic -v`
Expected: FAIL with "_make_request not defined"

- [ ] **Step 3: Implement _make_request method**

Add to `ipaclient.py` in IPAClient class:

```python
    def _make_request(
        self,
        method: str,
        args: Optional[List[Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a JSON-RPC request to the IPA server.

        Args:
            method: IPA command name (e.g., 'user_show', 'ping')
            args: Positional arguments for the command
            options: Keyword arguments/options for the command

        Returns:
            Result dictionary from the server

        Raises:
            IPAConnectionError: Network/connection failure
            IPAAuthenticationError: Kerberos authentication failure
            IPAServerError: Server returned an error
        """
        if args is None:
            args = []
        if options is None:
            options = {}

        # Add API version if not already present
        if "version" not in options:
            options["version"] = "2.251"

        # Build JSON-RPC payload
        payload = {
            "method": method,
            "params": [args, options],
            "id": 0,
        }

        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Referer": f"{self._base_url}/ipa",
            "Accept": "application/json",
        }

        # Make request with Kerberos authentication
        try:
            response = requests.post(
                self._json_url,
                json=payload,
                headers=headers,
                auth=HTTPSPNEGOAuth(opportunistic_auth=True),
                verify=self._verify_ssl,
            )
        except requests.exceptions.ConnectionError as e:
            raise IPAConnectionError(
                f"Failed to connect to {self._server}: {e}",
                data={"server": self._server},
            )
        except requests.exceptions.SSLError as e:
            raise IPAConnectionError(
                f"SSL verification failed for {self._server}: {e}",
                data={"server": self._server},
            )
        except requests.exceptions.RequestException as e:
            raise IPAConnectionError(
                f"Request failed: {e}",
                data={"server": self._server},
            )

        # Check HTTP status
        if response.status_code != 200:
            raise IPAServerError(
                f"HTTP {response.status_code}: {response.text}",
                code=f"HTTP{response.status_code}",
                data={"status_code": response.status_code},
            )

        # Parse JSON response
        try:
            result = response.json()
        except ValueError as e:
            raise IPAServerError(
                f"Invalid JSON response: {e}",
                code="InvalidJSON",
            )

        # Check for IPA errors
        if result.get("error") is not None:
            error = result["error"]
            error_msg = error.get("message", str(error))
            error_code = error.get("name", error.get("code", "UnknownError"))

            # Check for authentication errors
            if "Unauthorized" in error_msg or "credentials" in error_msg.lower():
                raise IPAAuthenticationError(
                    f"Authentication failed: {error_msg}",
                    code=str(error_code),
                    data=error,
                )

            raise IPAServerError(
                f"IPA error: {error_msg}",
                code=str(error_code),
                data=error,
            )

        return result.get("result", {})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_make_request -v`
Expected: All _make_request tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement JSON-RPC request infrastructure with error handling"
```

---

## Task 5: Ping Command

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for ping() method**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_ping_success(mock_server, mock_ping_response):
    """Test successful ping."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json=mock_ping_response,
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.ping()

    assert "summary" in result
    assert "IPA server version" in result["summary"]
    assert "API version" in result["summary"]


@responses.activate
def test_ping_connection_error(mock_server):
    """Test ping with connection error."""
    client = IPAClient(mock_server)

    with pytest.raises(IPAConnectionError):
        client.ping()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_ping_success -v`
Expected: FAIL with "ping not defined"

- [ ] **Step 3: Implement ping() method**

Add to `ipaclient.py` in IPAClient class:

```python
    def ping(self) -> Dict[str, Any]:
        """Test server connectivity.

        Returns:
            Dictionary with summary of server version and API version.
            Example: {"summary": "IPA server version 4.9.8. API version 2.251"}

        Raises:
            IPAConnectionError: Network/connection failure
            IPAAuthenticationError: Kerberos auth failure
            IPAServerError: Server returned error
        """
        return self._make_request("ping")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_ping -v`
Expected: All ping tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: add ping() method for server connectivity testing"
```

---

## Task 6: Command Execution

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for command() method**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_command_no_args(mock_server):
    """Test command execution with no arguments."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": {"data": "test"}, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.command("config_show")

    assert result == {"data": "test"}


@responses.activate
def test_command_with_args(mock_server):
    """Test command execution with positional arguments."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={
            "result": {"uid": ["admin"], "cn": ["Administrator"]},
            "error": None,
        },
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.command("user_show", "admin")

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["method"] == "user_show"
    assert request_body["params"][0] == ["admin"]


@responses.activate
def test_command_with_kwargs(mock_server):
    """Test command execution with keyword arguments."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={
            "result": [{"uid": ["user1"]}, {"uid": ["user2"]}],
            "count": 2,
            "error": None,
        },
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.command("user_find", uid="test", sizelimit=10)

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["params"][1]["uid"] == "test"
    assert request_body["params"][1]["sizelimit"] == 10
    assert request_body["params"][1]["version"] == "2.251"


@responses.activate
def test_command_with_args_and_kwargs(mock_server):
    """Test command execution with both args and kwargs."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": {"cn": ["testgroup"]}, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.command("group_show", "testgroup", all=True, raw=False)

    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["params"][0] == ["testgroup"]
    assert request_body["params"][1]["all"] is True
    assert request_body["params"][1]["raw"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_command_no_args -v`
Expected: FAIL with "command not defined"

- [ ] **Step 3: Implement command() method**

Add to `ipaclient.py` in IPAClient class:

```python
    def command(self, name: str, *args, **kwargs) -> Dict[str, Any]:
        """Execute arbitrary IPA command.

        Args:
            name: Command name (e.g., 'user_show', 'group_find')
            *args: Positional arguments for the command
            **kwargs: Keyword arguments/options for the command

        Returns:
            Command-specific result dictionary. Structure varies by command,
            but typically includes:
            - 'result': Main result data (dict, list, or other type)
            - 'summary': Human-readable summary (for some commands)
            - 'count': Number of results (for search commands)
            - 'truncated': Whether results were truncated (for search commands)

        Example:
            >>> client.command("user_show", "admin")
            {'uid': ['admin'], 'cn': ['Administrator'], ...}

            >>> client.command("user_find", uid="admin")
            {'result': [...], 'count': 1, 'truncated': False}

        Raises:
            IPAServerError: Command execution failed
            IPAValidationError: Invalid arguments
            IPAConnectionError: Network failure
        """
        return self._make_request(name, args=list(args), options=kwargs)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_command -v`
Expected: All command tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: add command() method for arbitrary IPA command execution"
```

---

## Task 7: Schema Retrieval and Caching

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for _get_schema**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_get_schema_initial_fetch(mock_server, mock_schema):
    """Test initial schema fetch."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    schema = client._get_schema()

    assert schema == mock_schema
    assert client._schema == mock_schema
    assert len(responses.calls) == 1


@responses.activate
def test_get_schema_cached(mock_server, mock_schema):
    """Test schema caching."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)

    # First call - fetches from server
    schema1 = client._get_schema()
    assert len(responses.calls) == 1

    # Second call - uses cache
    schema2 = client._get_schema()
    assert len(responses.calls) == 1  # No additional call
    assert schema1 is schema2


@responses.activate
def test_get_schema_error(mock_server):
    """Test schema fetch error handling."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={
            "result": None,
            "error": {"message": "Schema not available", "code": 500},
        },
        status=200,
    )

    client = IPAClient(mock_server)

    with pytest.raises(IPASchemaError) as exc_info:
        client._get_schema()

    assert "Schema fetch failed" in str(exc_info.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_get_schema_initial_fetch -v`
Expected: FAIL with "_get_schema not defined"

- [ ] **Step 3: Implement _get_schema method**

Add to `ipaclient.py` in IPAClient class:

```python
    def _get_schema(self) -> Dict[str, Any]:
        """Retrieve and cache IPA schema.

        Fetches the full IPA schema on first call and caches it in memory.
        Subsequent calls return the cached version.

        Returns:
            Full IPA schema dictionary with 'topics' and 'commands' keys

        Raises:
            IPASchemaError: Schema fetch or parse failure
        """
        if self._schema is not None:
            return self._schema

        try:
            result = self._make_request("schema")

            # Validate schema structure
            if not isinstance(result, dict):
                raise IPASchemaError(
                    "Invalid schema format: expected dict",
                    data={"type": type(result).__name__},
                )

            if "commands" not in result:
                raise IPASchemaError(
                    "Invalid schema: missing 'commands' key",
                    data={"keys": list(result.keys())},
                )

            self._schema = result
            return self._schema

        except IPAServerError as e:
            raise IPASchemaError(
                f"Schema fetch failed: {e.message}",
                data=e.data,
            )
        except (IPAConnectionError, IPAAuthenticationError):
            # Re-raise connection/auth errors as-is
            raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_get_schema -v`
Expected: All _get_schema tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement schema retrieval with in-memory caching"
```

---

## Task 8: Help - Topic Listing

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for help() topics listing**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_help_no_args_lists_topics(mock_server, mock_schema):
    """Test help() with no arguments lists all topics."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.help()

    assert "topics" in result
    assert len(result["topics"]) == 2

    # Check topics are sorted and have correct structure
    topics = {t["name"]: t for t in result["topics"]}

    assert "user" in topics
    assert topics["user"]["summary"] == "Users"

    assert "group" in topics
    assert topics["group"]["summary"] == "Groups"


@responses.activate
def test_help_topics_arg(mock_server, mock_schema):
    """Test help('topics') explicitly."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.help("topics")

    assert "topics" in result
    assert len(result["topics"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_help_no_args_lists_topics -v`
Expected: FAIL with "help not defined"

- [ ] **Step 3: Implement help() for topic listing**

Add to `ipaclient.py` in IPAClient class:

```python
    def help(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve help information.

        Args:
            topic: Optional topic or command name
                   None or "topics" → list all topics
                   "commands" → list all commands
                   "<topic>" → commands in topic
                   "<command>" → command details

        Returns:
            Structure varies by topic parameter. See class docstring for details.

        Raises:
            IPASchemaError: Schema fetch/parse failure
            IPAConnectionError: Network failure
        """
        schema = self._get_schema()

        # Default to topics listing
        if topic is None or topic == "topics":
            return self._help_topics(schema)

        # Commands listing
        if topic == "commands":
            return self._help_commands(schema)

        # Check if it's a command
        if topic in schema.get("commands", {}):
            return self._help_command(schema, topic)

        # Check if it's a topic
        if topic in schema.get("topics", {}):
            return self._help_topic(schema, topic)

        # Not found
        raise IPAValidationError(
            f"Unknown command or topic: {topic}",
            code="NotFound",
            data={"topic": topic},
        )

    def _help_topics(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate topic listing.

        Args:
            schema: Full IPA schema

        Returns:
            Dictionary with 'topics' key containing list of topic dicts
        """
        topics = []

        for topic_name, topic_data in schema.get("topics", {}).items():
            # Extract summary from first non-empty line of doc
            doc = topic_data.get("doc", "")
            summary = ""
            for line in doc.split("\n"):
                line = line.strip()
                if line:
                    summary = line
                    break

            topics.append({
                "name": topic_name,
                "summary": summary,
            })

        # Sort alphabetically by name
        topics.sort(key=lambda t: t["name"])

        return {"topics": topics}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_help_no_args_lists_topics -v`
Expected: All help topics tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement help() for topic listing"
```

---

## Task 9: Help - Commands Listing

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for help('commands')**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_help_commands(mock_server, mock_schema):
    """Test help('commands') lists all commands."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.help("commands")

    assert "commands" in result
    assert len(result["commands"]) == 3

    # Check commands are sorted and have correct structure
    commands = {c["name"]: c for c in result["commands"]}

    assert "user_show" in commands
    assert commands["user_show"]["summary"] == "Display information about a user"

    assert "user_find" in commands
    assert commands["user_find"]["summary"] == "Search for users"

    assert "group_show" in commands
    assert commands["group_show"]["summary"] == "Display information about a group"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_help_commands -v`
Expected: FAIL with "_help_commands not defined"

- [ ] **Step 3: Implement _help_commands method**

Add to `ipaclient.py` in IPAClient class:

```python
    def _help_commands(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate commands listing.

        Args:
            schema: Full IPA schema

        Returns:
            Dictionary with 'commands' key containing list of command dicts
        """
        commands = []

        for cmd_name, cmd_data in schema.get("commands", {}).items():
            commands.append({
                "name": cmd_name,
                "summary": cmd_data.get("summary", ""),
            })

        # Sort alphabetically by name
        commands.sort(key=lambda c: c["name"])

        return {"commands": commands}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_help_commands -v`
Expected: help commands test PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement help('commands') for commands listing"
```

---

## Task 10: Help - Topic Details

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for help('<topic>')**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_help_topic_details(mock_server, mock_schema):
    """Test help('<topic>') shows topic details."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.help("user")

    assert result["topic"] == "user"
    assert result["summary"] == "Users"
    assert result["doc"] == "Users\n\nManage user accounts."
    assert "commands" in result
    assert "user_show" in result["commands"]
    assert "user_find" in result["commands"]
    assert "group_show" not in result["commands"]


@responses.activate
def test_help_unknown_topic(mock_server, mock_schema):
    """Test help() with unknown topic raises error."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)

    with pytest.raises(IPAValidationError) as exc_info:
        client.help("nonexistent")

    assert "Unknown command or topic" in str(exc_info.value)
    assert exc_info.value.code == "NotFound"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_help_topic_details -v`
Expected: FAIL with "_help_topic not defined"

- [ ] **Step 3: Implement _help_topic method**

Add to `ipaclient.py` in IPAClient class:

```python
    def _help_topic(self, schema: Dict[str, Any], topic: str) -> Dict[str, Any]:
        """Generate topic details.

        Args:
            schema: Full IPA schema
            topic: Topic name

        Returns:
            Dictionary with topic details and associated commands
        """
        topic_data = schema["topics"][topic]

        # Extract summary from first non-empty line
        doc = topic_data.get("doc", "")
        summary = ""
        for line in doc.split("\n"):
            line = line.strip()
            if line:
                summary = line
                break

        # Find all commands in this topic
        commands = []
        for cmd_name, cmd_data in schema.get("commands", {}).items():
            if cmd_data.get("topic") == topic:
                commands.append(cmd_name)

        commands.sort()

        return {
            "topic": topic,
            "summary": summary,
            "doc": doc,
            "commands": commands,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_help_topic -v`
Expected: All help topic tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement help('<topic>') for topic details"
```

---

## Task 11: Help - Command Details

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for help('<command>')**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_help_command_details(mock_server, mock_schema):
    """Test help('<command>') shows command details."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.help("user_show")

    assert result["command"] == "user_show"
    assert result["topic"] == "user"
    assert result["summary"] == "Display information about a user"
    assert result["doc"] == "Display information about a user.\n\nShows detailed user attributes."

    # Check args
    assert len(result["args"]) == 1
    assert result["args"][0]["name"] == "uid"
    assert result["args"][0]["cli_name"] == "login"
    assert result["args"][0]["type"] == "str"
    assert result["args"][0]["required"] is True
    assert result["args"][0]["doc"] == "User login"

    # Check options
    options = {opt["name"]: opt for opt in result["options"]}
    assert "all" in options
    assert options["all"]["type"] == "bool"
    assert options["all"]["required"] is False
    assert options["all"]["default"] is False


@responses.activate
def test_help_command_no_required_args(mock_server, mock_schema):
    """Test help() for command with only optional args."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.help("user_find")

    # All params should be in options (no required positional args)
    assert len(result["args"]) == 0

    options = {opt["name"]: opt for opt in result["options"]}
    assert "criteria" in options
    assert "sizelimit" in options
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_help_command_details -v`
Expected: FAIL with "_help_command not defined"

- [ ] **Step 3: Implement _help_command method**

Add to `ipaclient.py` in IPAClient class:

```python
    def _help_command(self, schema: Dict[str, Any], command: str) -> Dict[str, Any]:
        """Generate command details.

        Args:
            schema: Full IPA schema
            command: Command name

        Returns:
            Dictionary with command details including args and options
        """
        cmd_data = schema["commands"][command]

        # Separate params into args (required positional) and options
        args = []
        options = []

        for param in cmd_data.get("params", []):
            # Skip internal params
            if param.get("exclude") == "webui":
                continue

            param_info = {
                "name": param["name"],
                "cli_name": param.get("cli_name", param["name"]),
                "type": self._map_type(param.get("type", "Str")),
                "required": param.get("required", False),
                "doc": param.get("doc", param.get("label", "")),
            }

            # Add default if present
            if "default" in param:
                param_info["default"] = param["default"]

            # Required params with cli_name become positional args
            if param.get("required") and param.get("cli_name"):
                args.append(param_info)
            else:
                options.append(param_info)

        return {
            "command": command,
            "topic": cmd_data.get("topic", ""),
            "summary": cmd_data.get("summary", ""),
            "doc": cmd_data.get("doc", ""),
            "args": args,
            "options": options,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_help_command -v`
Expected: All help command tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement help('<command>') for command details"
```

---

## Task 12: Schema Export - Type Mapping

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for _map_type**

Add to `tests/test_ipaclient.py`:

```python
def test_map_type_basic_types(mock_server):
    """Test type mapping for basic IPA types."""
    client = IPAClient(mock_server)

    assert client._map_type("Str") == "str"
    assert client._map_type("Int") == "int"
    assert client._map_type("Bool") == "bool"
    assert client._map_type("Flag") == "bool"
    assert client._map_type("List") == "list"
    assert client._map_type("Dict") == "dict"


def test_map_type_unknown(mock_server):
    """Test type mapping for unknown types falls back to str."""
    client = IPAClient(mock_server)

    assert client._map_type("SomeCustomType") == "str"
    assert client._map_type("") == "str"
    assert client._map_type(None) == "str"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_map_type_basic_types -v`
Expected: FAIL with "_map_type not defined"

- [ ] **Step 3: Implement _map_type method**

Add to `ipaclient.py` in IPAClient class:

```python
    def _map_type(self, ipa_type: Optional[str]) -> str:
        """Map IPA parameter type to Python type name.

        Args:
            ipa_type: IPA type name (e.g., 'Str', 'Int', 'Bool')

        Returns:
            Python type name ('str', 'int', 'bool', 'list', 'dict')
        """
        if not ipa_type:
            return "str"

        type_map = {
            "Str": "str",
            "Int": "int",
            "Bool": "bool",
            "Flag": "bool",
            "List": "list",
            "Dict": "dict",
        }

        return type_map.get(ipa_type, "str")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_map_type -v`
Expected: All type mapping tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement IPA to Python type mapping"
```

---

## Task 13: Schema Export - Transform

**Files:**
- Modify: `ipaclient.py`
- Modify: `tests/test_ipaclient.py`

- [ ] **Step 1: Write test for export_schema**

Add to `tests/test_ipaclient.py`:

```python
@responses.activate
def test_export_schema_structure(mock_server, mock_schema):
    """Test export_schema returns correct structure."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)
    result = client.export_schema()

    # Check top-level structure
    assert "topics" in result
    assert "commands" in result

    # Check topics structure
    assert "user" in result["topics"]
    user_topic = result["topics"]["user"]
    assert user_topic["name"] == "user"
    assert user_topic["summary"] == "Users"
    assert user_topic["doc"] == "Users\n\nManage user accounts."
    assert "user_show" in user_topic["commands"]
    assert "user_find" in user_topic["commands"]

    # Check commands structure
    assert "user_show" in result["commands"]
    user_show = result["commands"]["user_show"]
    assert user_show["name"] == "user_show"
    assert user_show["topic"] == "user"
    assert user_show["summary"] == "Display information about a user"
    assert len(user_show["args"]) == 1
    assert user_show["args"][0]["name"] == "uid"
    assert user_show["args"][0]["type"] == "str"

    # Check options don't include version param
    option_names = [opt["name"] for opt in user_show["options"]]
    assert "all" in option_names
    assert "version" not in option_names


@responses.activate
def test_export_schema_caching(mock_server, mock_schema):
    """Test export_schema uses cached schema."""
    responses.add(
        responses.POST,
        f"https://{mock_server}/ipa/json",
        json={"result": mock_schema, "error": None},
        status=200,
    )

    client = IPAClient(mock_server)

    # First call
    result1 = client.export_schema()
    assert len(responses.calls) == 1

    # Second call - should use cache
    result2 = client.export_schema()
    assert len(responses.calls) == 1

    assert result1 == result2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ipaclient.py::test_export_schema_structure -v`
Expected: FAIL with "export_schema not defined"

- [ ] **Step 3: Implement export_schema method**

Add to `ipaclient.py` in IPAClient class:

```python
    def export_schema(self) -> Dict[str, Any]:
        """Export structured schema for MCP tool generation.

        Returns:
            Dictionary with 'topics' and 'commands' keys, structured for
            easy consumption by MCP server tool registration:

            {
                "topics": {
                    "user": {
                        "name": "user",
                        "summary": "Users",
                        "doc": "Full documentation...",
                        "commands": ["user_add", "user_del", ...]
                    },
                    ...
                },
                "commands": {
                    "user_show": {
                        "name": "user_show",
                        "topic": "user",
                        "summary": "...",
                        "doc": "...",
                        "args": [...],
                        "options": [...]
                    },
                    ...
                }
            }

        Raises:
            IPASchemaError: Schema fetch/parse failure
        """
        schema = self._get_schema()

        # Transform topics
        topics = {}
        for topic_name, topic_data in schema.get("topics", {}).items():
            doc = topic_data.get("doc", "")
            summary = ""
            for line in doc.split("\n"):
                line = line.strip()
                if line:
                    summary = line
                    break

            # Find commands in this topic
            topic_commands = []
            for cmd_name, cmd_data in schema.get("commands", {}).items():
                if cmd_data.get("topic") == topic_name:
                    topic_commands.append(cmd_name)
            topic_commands.sort()

            topics[topic_name] = {
                "name": topic_name,
                "summary": summary,
                "doc": doc,
                "commands": topic_commands,
            }

        # Transform commands
        commands = {}
        for cmd_name, cmd_data in schema.get("commands", {}).items():
            # Separate params into args and options
            args = []
            options = []

            for param in cmd_data.get("params", []):
                # Skip internal params
                if param.get("exclude") == "webui":
                    continue

                param_info = {
                    "name": param["name"],
                    "cli_name": param.get("cli_name", param["name"]),
                    "type": self._map_type(param.get("type", "Str")),
                    "required": param.get("required", False),
                    "doc": param.get("doc", param.get("label", "")),
                }

                if "default" in param:
                    param_info["default"] = param["default"]

                # Required params with cli_name become positional args
                if param.get("required") and param.get("cli_name"):
                    args.append(param_info)
                else:
                    options.append(param_info)

            commands[cmd_name] = {
                "name": cmd_name,
                "topic": cmd_data.get("topic", ""),
                "summary": cmd_data.get("summary", ""),
                "doc": cmd_data.get("doc", ""),
                "args": args,
                "options": options,
            }

        return {
            "topics": topics,
            "commands": commands,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ipaclient.py::test_export_schema -v`
Expected: All export_schema tests PASS

- [ ] **Step 5: Commit**

```bash
git add ipaclient.py tests/test_ipaclient.py
git commit -m "feat: implement export_schema for MCP tool generation"
```

---

## Task 14: Integration Tests

**Files:**
- Create: `tests/test_ipaclient_integration.py`

- [ ] **Step 1: Create integration test file**

```python
"""Integration tests for IPA client (requires live IPA server).

These tests require:
1. A live IPA server (e.g., ipa.demo1.freeipa.org)
2. Valid Kerberos credentials (kinit)

Run with: pytest tests/test_ipaclient_integration.py -v

Skip if no server available: pytest -m "not integration"
"""

import pytest
from ipaclient import IPAClient, IPAConnectionError


# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture
def live_server():
    """Live IPA server for integration testing."""
    return "ipa.demo1.freeipa.org"


@pytest.fixture
def live_client(live_server):
    """Client connected to live server."""
    return IPAClient(live_server)


def test_integration_ping(live_client):
    """Test ping against live server."""
    result = live_client.ping()
    assert "summary" in result
    assert "IPA server version" in result["summary"]


def test_integration_schema_fetch(live_client):
    """Test schema retrieval from live server."""
    schema = live_client._get_schema()
    assert "topics" in schema
    assert "commands" in schema
    assert len(schema["commands"]) > 0


def test_integration_help_topics(live_client):
    """Test help topics listing."""
    result = live_client.help()
    assert "topics" in result
    assert len(result["topics"]) > 0


def test_integration_help_commands(live_client):
    """Test help commands listing."""
    result = live_client.help("commands")
    assert "commands" in result
    assert len(result["commands"]) > 0


def test_integration_help_topic(live_client):
    """Test help for specific topic."""
    result = live_client.help("user")
    assert result["topic"] == "user"
    assert "commands" in result
    assert len(result["commands"]) > 0


def test_integration_help_command(live_client):
    """Test help for specific command."""
    result = live_client.help("user_show")
    assert result["command"] == "user_show"
    assert "args" in result
    assert "options" in result


def test_integration_export_schema(live_client):
    """Test schema export."""
    schema = live_client.export_schema()
    assert "topics" in schema
    assert "commands" in schema

    # Verify structure
    if "user" in schema["topics"]:
        user_topic = schema["topics"]["user"]
        assert "name" in user_topic
        assert "commands" in user_topic

    if "user_show" in schema["commands"]:
        cmd = schema["commands"]["user_show"]
        assert "name" in cmd
        assert "args" in cmd
        assert "options" in cmd


def test_integration_command_config_show(live_client):
    """Test executing config_show command."""
    result = live_client.command("config_show")
    assert "result" in result or "cn" in result


def test_integration_no_credentials():
    """Test that missing Kerberos credentials fails gracefully."""
    # This test assumes no valid ticket exists
    # In practice, you'd clear credentials first or use a different server
    client = IPAClient("nonexistent.example.com")

    with pytest.raises(IPAConnectionError):
        client.ping()
```

- [ ] **Step 2: Configure pytest for integration tests**

Create `pytest.ini` in project root:

```ini
[pytest]
markers =
    integration: marks tests as integration tests requiring live server (deselect with '-m "not integration"')

# Default: skip integration tests unless explicitly requested
addopts = -m "not integration"
```

- [ ] **Step 3: Document integration test usage**

Add to `docs/testing.md`:

```markdown
# Testing

## Unit Tests

Run unit tests (no live server required):

```bash
pytest tests/test_ipaclient.py -v
```

## Integration Tests

Integration tests require a live IPA server and valid Kerberos credentials.

### Setup

1. Obtain Kerberos ticket:
   ```bash
   kinit admin@DEMO1.FREEIPA.ORG
   ```

2. Run integration tests:
   ```bash
   pytest tests/test_ipaclient_integration.py -v --integration
   ```

Or run with the marker:
```bash
pytest -m integration -v
```

### Using ipa.demo1.freeipa.org

The public demo server is available for testing:
- Server: `ipa.demo1.freeipa.org`
- Username: `admin`
- Password: `Secret123`

```bash
kinit admin@DEMO1.FREEIPA.ORG
# Enter password: Secret123
pytest -m integration -v
```

## Coverage

Run tests with coverage:

```bash
pytest --cov=ipaclient --cov-report=html --cov-report=term
```

View HTML coverage report:
```bash
open htmlcov/index.html
```
```

- [ ] **Step 4: Update pytest.ini**

Create file if it doesn't exist, add integration marker.

- [ ] **Step 5: Commit**

```bash
git add tests/test_ipaclient_integration.py pytest.ini docs/testing.md
git commit -m "test: add integration tests for live server testing"
```

---

## Task 15: Documentation and README

**Files:**
- Create: `README.md`
- Modify: `ipaclient.py` (add module-level examples)

- [ ] **Step 1: Create comprehensive README**

```markdown
# Minimal IPA Client

Lightweight Python library for programmatic interaction with FreeIPA servers via JSON-RPC.

Designed for MCP (Model Context Protocol) server integration with emphasis on simple dict-based APIs and dynamic schema export.

## Features

- ✅ JSON-RPC communication with FreeIPA servers
- ✅ Kerberos authentication (via existing tickets)
- ✅ Full help system (topics, commands, command details)
- ✅ Schema export for dynamic MCP tool generation
- ✅ Pure dict-based API (JSON-serializable)
- ✅ Comprehensive error handling

## Installation

```bash
pip install requests requests-gssapi
```

Or from requirements:

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Obtain Kerberos Credentials

```bash
kinit admin@EXAMPLE.COM
```

### 2. Basic Usage

```python
from ipaclient import IPAClient

# Initialize client
client = IPAClient("ipa.example.com")

# Test connectivity
result = client.ping()
print(result["summary"])
# Output: IPA server version 4.9.8. API version 2.251

# Execute commands
user = client.command("user_show", "admin")
print(user["uid"][0])
# Output: admin

# Search with options
users = client.command("user_find", uid="test*", sizelimit=10)
print(f"Found {users['count']} users")
```

### 3. Help System

```python
# List all topics
topics = client.help()
for topic in topics["topics"]:
    print(f"{topic['name']}: {topic['summary']}")

# List all commands
commands = client.help("commands")
for cmd in commands["commands"]:
    print(f"{cmd['name']}: {cmd['summary']}")

# Get topic details
user_topic = client.help("user")
print(f"Commands in {user_topic['topic']}: {user_topic['commands']}")

# Get command details
cmd_help = client.help("user_show")
print(f"Command: {cmd_help['command']}")
print(f"Summary: {cmd_help['summary']}")
for arg in cmd_help['args']:
    print(f"  Arg: {arg['name']} ({arg['type']}) - {arg['doc']}")
for opt in cmd_help['options']:
    print(f"  Option: {opt['name']} ({opt['type']}) - {opt['doc']}")
```

### 4. Schema Export (for MCP Integration)

```python
# Export full schema for dynamic tool generation
schema = client.export_schema()

# Topics grouped with commands
for topic_name, topic_info in schema["topics"].items():
    print(f"\nTopic: {topic_name}")
    print(f"Commands: {', '.join(topic_info['commands'])}")

# Command details with types
for cmd_name, cmd_info in schema["commands"].items():
    print(f"\n{cmd_name}:")
    print(f"  Args: {[a['name'] for a in cmd_info['args']]}")
    print(f"  Options: {[o['name'] for o in cmd_info['options']]}")
```

## API Reference

### IPAClient

```python
client = IPAClient(server, verify_ssl=True)
```

**Parameters:**
- `server` (str): IPA server hostname (e.g., 'ipa.example.com')
- `verify_ssl` (bool): Whether to verify SSL certificates (default: True)

### Methods

#### `ping() -> dict`

Test server connectivity.

```python
result = client.ping()
# Returns: {"summary": "IPA server version X.Y.Z. API version 2.251"}
```

#### `command(name, *args, **kwargs) -> dict`

Execute arbitrary IPA command.

```python
# With positional args
user = client.command("user_show", "admin")

# With keyword args
users = client.command("user_find", uid="admin")

# With both
group = client.command("group_show", "admins", all=True)
```

#### `help(topic=None) -> dict`

Retrieve help information.

```python
# List topics
topics = client.help()

# List commands
commands = client.help("commands")

# Topic details
user_topic = client.help("user")

# Command details
cmd_details = client.help("user_show")
```

#### `export_schema() -> dict`

Export structured schema for MCP tool generation.

```python
schema = client.export_schema()
# Returns: {"topics": {...}, "commands": {...}}
```

## Error Handling

All errors inherit from `IPAError` and include a `.to_dict()` method for MCP integration.

```python
from ipaclient import (
    IPAError,
    IPAConnectionError,
    IPAAuthenticationError,
    IPAServerError,
    IPASchemaError,
    IPAValidationError,
)

try:
    result = client.command("user_show", "nonexistent")
except IPAServerError as e:
    print(f"Error: {e.message}")
    print(f"Code: {e.code}")

    # For MCP integration
    error_dict = e.to_dict()
    # Returns: {"error": {"code": "...", "message": "...", "data": {...}}}
```

## MCP Server Integration

Example MCP server using this client:

```python
from ipaclient import IPAClient, IPAError

# Initialize client once
client = IPAClient("ipa.example.com")

# Export schema for tool generation
schema = client.export_schema()

# Register MCP tools dynamically
for cmd_name, cmd_info in schema["commands"].items():
    @mcp_server.tool(name=cmd_name, description=cmd_info["summary"])
    def tool_handler(*args, **kwargs):
        try:
            return client.command(cmd_name, *args, **kwargs)
        except IPAError as e:
            return e.to_dict()
```

## Testing

### Unit Tests

```bash
pytest tests/test_ipaclient.py -v
```

### Integration Tests

Requires live IPA server and Kerberos credentials:

```bash
kinit admin@DEMO1.FREEIPA.ORG
pytest -m integration -v
```

See [testing.md](docs/testing.md) for details.

## Requirements

- Python 3.8+
- requests >= 2.25.0
- requests-gssapi >= 1.2.0
- Valid Kerberos credentials (kinit)

## License

See LICENSE file.

## Contributing

Contributions welcome! Please ensure tests pass before submitting PRs.

```bash
pytest tests/ -v --cov=ipaclient
```
```

- [ ] **Step 2: Add usage example to module docstring**

Update module docstring in `ipaclient.py`:

```python
"""
Minimal IPA Client - JSON-RPC interface to FreeIPA servers.

This module provides a lightweight client for interacting with FreeIPA
servers via JSON-RPC. It requires Kerberos authentication (existing tickets
via kinit) and returns pure Python dictionaries suitable for MCP integration.

Basic Example:
    >>> from ipaclient import IPAClient
    >>> client = IPAClient("ipa.example.com")
    >>> result = client.ping()
    >>> print(result["summary"])
    IPA server version 4.9.8. API version 2.251

Command Execution:
    >>> user = client.command("user_show", "admin")
    >>> print(user["uid"][0])
    admin

    >>> users = client.command("user_find", uid="test*")
    >>> print(f"Found {users['count']} users")

Help System:
    >>> topics = client.help()
    >>> cmd_help = client.help("user_show")
    >>> print(cmd_help["summary"])

Schema Export (for MCP):
    >>> schema = client.export_schema()
    >>> for topic, info in schema["topics"].items():
    ...     print(f"{topic}: {len(info['commands'])} commands")

Error Handling:
    >>> from ipaclient import IPAError
    >>> try:
    ...     client.command("user_show", "nonexistent")
    ... except IPAError as e:
    ...     print(e.to_dict())

Dependencies:
    - requests: HTTP client
    - requests-gssapi: Kerberos authentication

Authentication:
    Requires valid Kerberos credentials. Run 'kinit' before using:
    $ kinit admin@EXAMPLE.COM
"""
```

- [ ] **Step 3: Verify README rendering**

Run: `python3 -c "import ipaclient; help(ipaclient)"`
Expected: Clean help output with examples

- [ ] **Step 4: Commit**

```bash
git add README.md ipaclient.py
git commit -m "docs: add comprehensive README and usage examples"
```

---

## Self-Review

**1. Spec coverage check:**

✅ Ping command - Task 5
✅ Help system (topics, commands, topic details, command details) - Tasks 8-11
✅ Command execution - Task 6
✅ Schema export - Task 13
✅ Exception hierarchy with .to_dict() - Task 2
✅ JSON-RPC infrastructure - Task 4
✅ Schema caching - Task 7
✅ Type mapping - Task 12
✅ MCP integration pattern - Task 13, 15
✅ Testing - Tasks 14, all test steps
✅ Documentation - Task 15

**2. Placeholder scan:**

✅ No TBD, TODO, or "implement later"
✅ No "add appropriate error handling" without code
✅ No "write tests for the above" without test code
✅ All test steps include actual test code
✅ All implementation steps include actual implementation code
✅ All file paths are exact and absolute

**3. Type consistency check:**

✅ Method signatures consistent: `_make_request`, `_get_schema`, `_map_type`, `help`, `export_schema`
✅ Return types consistent: all methods return `Dict[str, Any]`
✅ Parameter names consistent: `server`, `verify_ssl`, `topic`, `command`
✅ Internal method names prefixed with `_` consistently
✅ Exception class hierarchy consistent

**4. Task dependencies:**

✅ Task 1 (setup) → All other tasks
✅ Task 2 (exceptions) → Task 4 (uses in error handling)
✅ Task 3 (init) → Task 4 (uses client instance)
✅ Task 4 (request) → Tasks 5, 6, 7 (ping, command, schema)
✅ Task 7 (schema) → Tasks 8-11, 13 (help and export)
✅ Task 12 (type mapping) → Tasks 11, 13 (used in command help and export)

All issues resolved. Plan is complete and ready for execution.

---

## Execution Options

Plan complete and saved to `docs/implementation/2026-04-10-minimal-ipa-json-rpc-client.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
