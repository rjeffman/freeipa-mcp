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
