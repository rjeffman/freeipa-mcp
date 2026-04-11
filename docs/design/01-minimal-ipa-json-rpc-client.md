# Design: Minimal IPA Client for MCP Integration

**Date:** 2026-04-10
**Status:** Implemented
**Implementation Date:** 2026-04-11

## Overview

A lightweight Python library for programmatic interaction with FreeIPA servers via JSON-RPC. Designed specifically for MCP (Model Context Protocol) server integration, with emphasis on simple dict-based APIs and dynamic schema export.

**Key Features:**
- JSON-RPC communication with IPA servers
- Kerberos authentication (via existing tickets)
- Full help system (topics, commands, detailed command help)
- Schema export for dynamic MCP tool generation
- Pure dict-based API (JSON-serializable)
- Comprehensive error handling

**File Structure:**
```
ipaclient.py           # Main module (~400-500 lines)
├── Exceptions         # IPAError hierarchy
├── IPAClient class    # Core client
└── Helper functions   # Schema parsing utilities
```

## Requirements Summary

1. **Authentication:** Kerberos only (existing tickets via kinit)
2. **Transport:** JSON-RPC over HTTPS
3. **Core Operations:**
   - Ping server
   - Retrieve help information (topics, commands, command details)
   - Execute arbitrary commands
   - Export structured schema
4. **Output Format:** Python dictionaries (JSON-serializable)
5. **Error Handling:** Custom exceptions with `.to_dict()` method
6. **Dependencies:** Minimal (requests, requests-gssapi)

## Public API

### Class: `IPAClient`

```python
class IPAClient:
    """Minimal IPA JSON-RPC client."""

    def __init__(self, server: str, verify_ssl: bool = True) -> None:
        """
        Initialize IPA client.

        Args:
            server: IPA server hostname (e.g., 'ipa.example.com')
            verify_ssl: Whether to verify SSL certificates
        """

    def ping(self) -> dict:
        """
        Test server connectivity.

        Returns:
            {"summary": "IPA server version X.Y.Z. API version 2.251"}

        Raises:
            IPAConnectionError: Network/connection failure
            IPAAuthenticationError: Kerberos auth failure
            IPAServerError: Server returned error
        """

    def help(self, topic: str = None) -> dict:
        """
        Retrieve help information.

        Args:
            topic: Optional topic/command name
                   None or "topics" → list all topics
                   "commands" → list all commands
                   "<topic>" → commands in topic
                   "<command>" → command details

        Returns:
            Structure varies by topic:

            Topics list:
            {
                "topics": [
                    {"name": "user", "summary": "Users"},
                    {"name": "group", "summary": "Groups"},
                    ...
                ]
            }

            Commands list:
            {
                "commands": [
                    {"name": "user_add", "summary": "Add a new user"},
                    ...
                ]
            }

            Topic details:
            {
                "topic": "user",
                "summary": "Users",
                "doc": "Full documentation...",
                "commands": ["user_add", "user_del", ...]
            }

            Command details:
            {
                "command": "user_show",
                "topic": "user",
                "summary": "Display information about a user",
                "doc": "Full documentation...",
                "args": [
                    {
                        "name": "uid",
                        "cli_name": "login",
                        "type": "str",
                        "required": true,
                        "doc": "User login"
                    }
                ],
                "options": [
                    {
                        "name": "all",
                        "cli_name": "all",
                        "type": "bool",
                        "required": false,
                        "default": false,
                        "doc": "Retrieve and print all attributes"
                    },
                    ...
                ]
            }

        Raises:
            IPASchemaError: Schema fetch/parse failure
            IPAConnectionError: Network failure
        """

    def command(self, name: str, *args, **kwargs) -> dict:
        """
        Execute arbitrary IPA command.

        Args:
            name: Command name (e.g., 'user_show', 'group_find')
            *args: Positional arguments
            **kwargs: Keyword arguments/options

        Returns:
            Command-specific result dict, typically:
            {
                "result": {...},      # Main result data
                "summary": "...",     # Human-readable summary
                "count": N,           # For search commands
                "truncated": bool     # For paginated results
            }

        Raises:
            IPAServerError: Command execution failed
            IPAValidationError: Invalid arguments
            IPAConnectionError: Network failure
        """

    def export_schema(self) -> dict:
        """
        Export structured schema for MCP tool generation.

        Returns:
            {
                "topics": {
                    "user": {
                        "name": "user",
                        "summary": "Users",
                        "doc": "Manage user accounts...",
                        "commands": ["user_add", "user_del", ...]
                    },
                    ...
                },
                "commands": {
                    "user_show": {
                        "name": "user_show",
                        "topic": "user",
                        "summary": "Display information about a user",
                        "doc": "Full command documentation...",
                        "args": [
                            {
                                "name": "uid",
                                "cli_name": "login",
                                "type": "str",
                                "required": true,
                                "doc": "User login"
                            }
                        ],
                        "options": [
                            {
                                "name": "all",
                                "cli_name": "all",
                                "type": "bool",
                                "required": false,
                                "default": false,
                                "doc": "Retrieve and print all attributes"
                            },
                            ...
                        ]
                    },
                    ...
                }
            }

        Raises:
            IPASchemaError: Schema fetch/parse failure
        """
```

### Exceptions

```python
class IPAError(Exception):
    """Base exception with .to_dict() for MCP integration."""

    def __init__(self, message: str, code: str = None, data: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.data = data or {}

    def to_dict(self) -> dict:
        """
        Convert to MCP-friendly error dict.

        Returns:
            {
                "error": {
                    "code": "...",
                    "message": "...",
                    "data": {...}
                }
            }
        """

class IPAConnectionError(IPAError):
    """Network/connection failures."""

class IPAAuthenticationError(IPAError):
    """Kerberos authentication failures."""

class IPAServerError(IPAError):
    """IPA server returned an error."""

class IPASchemaError(IPAError):
    """Schema fetch/parse failures."""

class IPAValidationError(IPAError):
    """Invalid parameters/arguments."""
```

## Internal Implementation Details

### Schema Caching Strategy

```python
class IPAClient:
    def __init__(self, server, verify_ssl=True):
        self._server = server
        self._base_url = f"https://{server}"
        self._json_url = f"{self._base_url}/ipa/json"
        self._verify_ssl = verify_ssl
        self._schema = None  # Cached schema (lazy loaded)
```

- Fetched on first `help()` or `export_schema()` call
- Stored in `self._schema` (instance variable)
- Lifetime: same as `IPAClient` instance
- No disk persistence (MCP server is long-running, keeps instance alive)

### JSON-RPC Protocol

```python
def _make_request(self, method, args=None, options=None):
    """Make a JSON-RPC request to the IPA server."""
    payload = {
        "method": method,
        "params": [args or [], options or {}],
        "id": 0
    }
    # Add API version to options
    if "version" not in payload["params"][1]:
        payload["params"][1]["version"] = "2.251"

    response = requests.post(
        self._json_url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Referer": f"{self._base_url}/ipa",
            "Accept": "application/json"
        },
        auth=HTTPSPNEGOAuth(opportunistic_auth=True),
        verify=self._verify_ssl
    )
    # Parse and return result
```

**Protocol Details:**
- URL: `https://{server}/ipa/json`
- Method: POST
- Headers:
  - `Content-Type: application/json`
  - `Referer: https://{server}/ipa`
  - `Accept: application/json`
- Auth: `HTTPSPNEGOAuth(opportunistic_auth=True)` from requests-gssapi
- Payload: `{"method": "...", "params": [[args], {options}], "id": 0}`
- Auto-inject `version: "2.251"` into options if not present

### Type Mapping (IPA → Python)

| IPA Type | Python Type |
|----------|-------------|
| `Str` | `"str"` |
| `Int` | `"int"` |
| `Bool`, `Flag` | `"bool"` |
| `List` | `"list"` |
| `Dict` | `"dict"` |
| Others | `"str"` (fallback) |

### Help Data Sources

- **Topics:** From `schema` command → `topics` dict
- **Commands:** From `schema` command → `commands` dict
- **Topic summaries:** First non-empty line of topic `doc` field
- **Command summaries:** `summary` field from schema
- **Full docs:** `doc` field from schema

### Data Flow

**1. Ping Operation:**
```
Client.ping()
  → _make_request("ping", [], {})
    → POST to /ipa/json with Kerberos auth
      → Parse JSON response
        → Return {"summary": "..."}
```

**2. Help Operation (first call):**
```
Client.help("user_show")
  → _get_schema() (cache miss)
    → _make_request("schema", [], {})
      → Parse massive JSON schema
        → Store in self._schema
  → _parse_help("user_show", self._schema)
    → Find command in schema
      → Extract args, options, docs
        → Return formatted dict
```

**3. Command Execution:**
```
Client.command("user_find", uid="admin")
  → _make_request("user_find", [], {"uid": "admin", "version": "2.251"})
    → POST to /ipa/json
      → Parse result
        → Return {"result": [...], "count": N, "summary": "..."}
```

**4. Schema Export:**
```
Client.export_schema()
  → _get_schema() (use cache if available)
  → _transform_schema_for_mcp(raw_schema)
    → Group commands by topic
      → Extract type information
        → Return structured dict
```

## Dependencies

**Required:**
- `requests` (>=2.25.0) - HTTP client
- `requests-gssapi` (>=1.2.0) - Kerberos authentication

**Optional:**
- `typing` (stdlib, Python 3.5+) - Type hints for better IDE support

**Total dependency footprint:** 2 external packages

## Testing Strategy

### Unit Tests (pytest)

1. **Connection tests:**
   - Valid server URL parsing
   - SSL verification settings
   - Kerberos auth header presence

2. **Request/response tests:**
   - Correct JSON-RPC payload format
   - Version auto-injection
   - Error response parsing

3. **Help functionality:**
   - Schema caching behavior
   - Topic listing
   - Command help parsing
   - Missing command/topic handling

4. **Command execution:**
   - Argument passing
   - Option passing
   - Result extraction

5. **Schema export:**
   - Structure validation
   - Type mapping correctness
   - Topic grouping

6. **Error handling:**
   - Connection failures → IPAConnectionError
   - HTTP errors → IPAServerError
   - IPA errors → IPAServerError
   - `.to_dict()` formatting

### Integration Tests (optional, requires live IPA server)

- Real ping test
- Real schema fetch
- Real command execution (read-only: user_show, config_show)

**Test Coverage Target:** >90%

## MCP Server Integration Pattern

```python
# MCP server initialization
client = IPAClient("ipa.example.com")

# Export schema to generate MCP tools dynamically
schema = client.export_schema()

# Register MCP tools based on schema
for cmd_name, cmd_info in schema["commands"].items():
    @mcp_server.tool(name=cmd_name, description=cmd_info["summary"])
    def tool_handler(*args, **kwargs):
        try:
            return client.command(cmd_name, *args, **kwargs)
        except IPAError as e:
            return e.to_dict()

# MCP tool calls map directly to client methods
# No additional state management needed
```

### Why This Design Works Well for MCP

1. **One class instance per MCP server** - The MCP server creates one IPAClient instance on startup, reuses it for all tool calls (efficient, maintains session)

2. **Methods map directly to MCP tools** - Each method becomes an MCP tool with identical signatures

3. **Pure dict outputs** - All returns are JSON-serializable dicts, perfect for MCP responses

4. **Stateless from caller perspective** - MCP tools don't need to manage connection state, just call methods

5. **Easy to configure** - MCP server config specifies IPA server URL once, done

6. **Dynamic tool generation** - `export_schema()` enables MCP server to discover and register all IPA commands automatically

## Non-Goals (Out of Scope)

- ❌ CLI interface (pure library)
- ❌ XML-RPC support (JSON-RPC only)
- ❌ Session-based authentication (Kerberos tickets only)
- ❌ Disk-based schema caching
- ❌ Helper methods for specific commands (use generic `command()`)
- ❌ Password-based authentication
- ❌ Custom output formatting (returns raw dicts)

## Design Principles

1. **Minimal abstraction** - Direct mapping to IPA JSON-RPC protocol
2. **MCP-first** - Dict-based API optimized for MCP integration
3. **Explicit over implicit** - No magic, clear method signatures
4. **Fail fast** - Raise exceptions immediately, let caller handle
5. **Cache wisely** - Schema cached in memory, no disk I/O
6. **Type safety** - Type hints throughout for better IDE support

## Success Criteria

- ✅ Can ping IPA server and verify connectivity
- ✅ Can retrieve help for topics and commands
- ✅ Can execute arbitrary IPA commands programmatically
- ✅ Can export full schema for MCP tool generation
- ✅ All outputs are JSON-serializable dicts
- ✅ Errors are catchable and convertible to dicts
- ✅ Code is under 500 lines
- ✅ Only 2 external dependencies
- ✅ Test coverage >90%

## Implementation Estimate

- **Core client (JSON-RPC):** ~100-150 lines
- **Exception classes:** ~50-75 lines
- **Help/schema parsing:** ~150-200 lines
- **Tests:** ~200-300 lines
- **Documentation/docstrings:** ~100-150 lines

**Total:** ~400-500 lines (excluding tests)

## Implementation Notes

**Implementation completed:** 2026-04-11

### What Was Built

All design requirements were successfully implemented:
- ✅ Core IPAClient with ping(), command(), help(), and export_schema()
- ✅ Complete exception hierarchy with to_dict() serialization
- ✅ Full help system (topics, commands, topic details, command details)
- ✅ Schema export for MCP tool generation
- ✅ 35 unit tests (100% pass rate)
- ✅ Integration tests for live server validation
- ✅ Comprehensive documentation (README.md, TESTING.md)

### Actual Implementation Size

- **ipaclient.py:** ~650 lines (vs. estimated 400-500)
- **Reason for increase:** Additional schema transformation logic for live server compatibility
- **tests/test_ipaclient.py:** ~350 lines (35 tests)
- **tests/test_ipaclient_integration.py:** ~100 lines

### Live Server Compatibility Fixes

During testing with `ipa.demo1.freeipa.org`, we discovered and fixed:

1. **Schema nesting:** Live server returns `{'result': {'commands': ...}}` not `{'commands': ...}`
   - Fixed: Added unwrapping logic in `_get_schema()`

2. **List-based schema structure:** Server returns commands/topics as lists, not dicts
   - Fixed: Transform lists to dicts keyed by name in `_get_schema()`

3. **Topic field variations:** Live schema uses `topic_topic` field with version suffix (e.g., "user/1")
   - Fixed: Extract base topic name from `topic_topic` field in `_help_command()`

4. **Missing summaries:** Some commands only have `doc` field populated
   - Fixed: Use first line of `doc` as fallback summary if `summary` is empty

These fixes ensure the client works with both mock test data and real IPA servers without breaking changes to the public API.

### Test Results

- **Unit tests:** 35/35 passing
- **Integration tests:** All passing against ipa.demo1.freeipa.org
- **Coverage:** >90%

### Files

- `ipaclient.py` - Main module
- `tests/test_ipaclient.py` - Unit tests
- `tests/test_ipaclient_integration.py` - Integration tests
- `tests/conftest.py` - Shared test fixtures
- `README.md` - User documentation
- `TESTING.md` - Testing instructions
- `pytest.ini` - Pytest configuration
- `requirements.txt` - Runtime dependencies
- `requirements-dev.txt` - Development dependencies
- `COPYING` - GPL v3 license

## Next Steps

1. ~~Write implementation plan~~ ✅ Done
2. ~~Implement core IPAClient class~~ ✅ Done
3. ~~Add exception hierarchy~~ ✅ Done
4. ~~Implement help system~~ ✅ Done
5. ~~Implement schema export~~ ✅ Done
6. ~~Write unit tests~~ ✅ Done
7. ~~Write integration tests~~ ✅ Done
8. Create MCP server using this client (future work)
