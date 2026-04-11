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
        data: Optional[Dict[str, Any]] = None,
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
        except requests.exceptions.SSLError as e:
            raise IPAConnectionError(
                f"SSL verification failed for {self._server}: {e}",
                data={"server": self._server},
            )
        except requests.exceptions.ConnectionError as e:
            raise IPAConnectionError(
                f"Failed to connect to {self._server}: {e}",
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
