# freeipa-mcp-py

A minimal Python client for interacting with FreeIPA servers via JSON-RPC. Designed as a foundation for Model Context Protocol (MCP) server integration, providing clean dictionary-based responses suitable for AI tool consumption.

## Features

- **Kerberos Authentication**: Uses existing Kerberos tickets (via `kinit`) for secure authentication
- **JSON-RPC Protocol**: Direct communication with FreeIPA's JSON-RPC API
- **Schema Introspection**: Fetch and explore the full IPA schema, including topics, commands, arguments, and options
- **Help System**: Built-in help for topics, commands, and parameter details
- **Schema Export**: Structured schema output for MCP tool generation
- **Type Mapping**: Automatic mapping of IPA parameter types to Python types
- **In-Memory Caching**: Schema is fetched once and cached for the session
- **Error Handling**: Typed exception hierarchy with `to_dict()` for MCP-friendly error responses
- **Pure Dictionary Output**: All methods return plain Python dicts, ready for JSON serialization

## Requirements

- Python 3.10+
- A FreeIPA server accessible over HTTPS
- Valid Kerberos credentials (`kinit`)

### System Dependencies

```bash
# Fedora/RHEL/CentOS
dnf install krb5-workstation krb5-devel

# Debian/Ubuntu
apt install krb5-user libkrb5-dev
```

### Python Dependencies

Core dependencies (defined in `pyproject.toml`):
- `requests>=2.25.0` - HTTP client
- `requests-gssapi>=1.2.0` - Kerberos authentication

Development dependencies:
- `pytest>=7.0.0` - Testing framework
- `pytest-cov>=4.0.0` - Coverage reporting
- `ruff>=0.15.10` - Linting and formatting
- `ty>=0.0.29` - Type checking
- `responses>=0.20.0` - HTTP mocking for tests

## Installation

```bash
git clone https://github.com/rjeffman/freeipa-mcp-py.git
cd freeipa-mcp-py
pip install -e .
```

For development (includes testing and linting tools):

```bash
pip install -e ".[dev]"
```

## Quick Start

### Authenticate with Kerberos

```bash
kinit admin@EXAMPLE.COM
```

### Basic Usage

```python
from ipaclient import IPAClient

# Connect to your IPA server
client = IPAClient("ipa.example.com")

# Test connectivity
result = client.ping()
print(result["summary"])
# "IPA server version 4.9.8. API version 2.251"
```

### Execute Commands

```python
# Show a user (result is nested under 'result' key)
user = client.command("user_show", "admin")
print("Username:", user["result"]["uid"][0])
print("Home:", user["result"]["homedirectory"][0])

# Search for users
results = client.command("user_find", uid="admin", sizelimit=10)
print(f"Found {results['count']} users")
for u in results['result']:
    print(f"  - {u['uid'][0]}")

# Show server configuration
config = client.command("config_show")
print("Domain:", config["result"]["cn"][0])
```

### Help System

```python
# List all topics
topics = client.help()
for t in topics["topics"]:
    print(f"{t['name']}: {t['summary']}")

# List all commands
commands = client.help("commands")
for c in commands["commands"]:
    print(f"{c['name']}: {c['summary']}")

# Get commands for a topic
user_help = client.help("user")
print(user_help["doc"])
for c in user_help["commands"]:
    print(f"  {c['name']}")

# Get command details
cmd = client.help("user_show")
print(f"Args: {cmd['args']}")
print(f"Options: {cmd['options']}")
```

### Help System (Markdown Format)

For AI agents and tools that prefer structured markdown:

```python
from ipaclient import IPAClient

client = IPAClient("ipa.example.com")

# Get all topics as markdown table
topics_md = client.help_markdown()
print(topics_md)
# Output:
# # IPA Help Topics
# | Topic | Description |
# |-------|-------------|
# | user | Users |
# | group | Groups |
# ...

# Get topic details with commands
user_topic_md = client.help_markdown("user")
print(user_topic_md)
# Output:
# # user
# Users
# Manage user entries. All users are POSIX users...
# ## Commands
# | Command | Description |
# |---------|-------------|
# | user_add | Add a new user. |
# ...

# Get command details with options
cmd_md = client.help_markdown("user_show")
print(cmd_md)
# Output:
# # user_show
# Display information about a user.
# ## Options
# | Option | Type | Description |
# |--------|------|-------------|
# | uid | str | User login |
# ...
```

All `help_markdown()` calls work with both old and new FreeIPA servers
by converting the structured JSON output from `help()` to markdown format.

### Schema Export

```python
# Export full schema for MCP tool generation
schema = client.export_schema()

# Iterate topics
for name, topic in schema["topics"].items():
    print(f"{name}: {topic['summary']} ({len(topic['commands'])} commands)")

# Iterate commands with their parameters
for name, cmd in schema["commands"].items():
    print(f"{name}: {cmd['summary']}")
    for arg in cmd["args"]:
        print(f"  arg: {arg['name']} ({arg['type']})")
    for opt in cmd["options"]:
        print(f"  opt: {opt['name']} ({opt['type']})")
```

## API Reference

### `IPAClient(server, verify_ssl=True)`

Create a new IPA client instance.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `server` | `str` | required | IPA server hostname (e.g., `"ipa.example.com"`) |
| `verify_ssl` | `bool` | `True` | Whether to verify SSL certificates. When `True`, the CA certificate is automatically downloaded from `http://{server}/ipa/config/ca.crt` and cached in `~/.cache/freeipa-mcp-py/certs/` for reuse across sessions. |

### Methods

#### `ping() -> dict`

Test server connectivity. Returns a dictionary with a `summary` key containing the server and API version.

#### `command(name, *args, **kwargs) -> dict`

Execute an arbitrary IPA command.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Command name (e.g., `"user_show"`, `"group_find"`) |
| `*args` | positional | Positional arguments for the command |
| `**kwargs` | keyword | Options/keyword arguments for the command |

#### `help(topic=None) -> dict`

Retrieve help information. Behavior depends on the `topic` parameter:

| `topic` value | Returns |
|---------------|---------|
| `None` or `"topics"` | List of all available topics |
| `"commands"` | List of all available commands |
| `"<topic_name>"` | Topic details with associated commands |
| `"<command_name>"` | Command details with args and options |

#### `export_schema() -> dict`

Export the full structured schema for MCP tool generation. Returns a dictionary with `topics` and `commands` keys, where each command includes its positional arguments and keyword options with type information.

### SSL Certificate Handling

By default, the client automatically handles SSL certificate verification:

1. **Automatic CA Certificate Download**: On first connection, the CA certificate is downloaded from `http://{server}/ipa/config/ca.crt`
2. **Persistent Caching**: Certificates are cached in `~/.cache/freeipa-mcp-py/certs/{server}.crt`
3. **Reuse Across Sessions**: Subsequent connections reuse the cached certificate without re-downloading

This eliminates `InsecureRequestWarning` warnings while maintaining security. To disable SSL verification (not recommended for production):

```python
client = IPAClient("ipa.example.com", verify_ssl=False)
```

## Error Handling

All exceptions inherit from `IPAError` and include a `to_dict()` method for MCP-friendly serialization.

```python
from ipaclient import (
    IPAClient,
    IPAError,
    IPAConnectionError,
    IPAAuthenticationError,
    IPAServerError,
    IPASchemaError,
    IPAValidationError,
)

client = IPAClient("ipa.example.com")

try:
    result = client.command("user_show", "nonexistent")
except IPAConnectionError as e:
    print(f"Connection failed: {e.message}")
    print(e.to_dict())  # {"error": {"code": "...", "message": "...", "data": {...}}}
except IPAAuthenticationError as e:
    print(f"Auth failed: {e.message}")
except IPAServerError as e:
    print(f"Server error: {e.message}")
    print(f"Error code: {e.code}")
    print(f"Error data: {e.data}")
except IPAError as e:
    print(f"IPA error: {e.message}")
```

### Exception Hierarchy

| Exception | Description |
|-----------|-------------|
| `IPAError` | Base exception for all IPA client errors |
| `IPAConnectionError` | Network or connection failure (SSL, DNS, timeout) |
| `IPAAuthenticationError` | Kerberos authentication failure |
| `IPAServerError` | IPA server returned an error response |
| `IPASchemaError` | Schema fetch or parse failure |
| `IPAValidationError` | Invalid parameters or arguments |

## MCP Server Integration

This client is designed to serve as the backend for an MCP server. Example integration pattern:

```python
from ipaclient import IPAClient, IPAError

client = IPAClient("ipa.example.com")

# Use export_schema() to register MCP tools dynamically
schema = client.export_schema()

for cmd_name, cmd_info in schema["commands"].items():
    # Register each IPA command as an MCP tool
    tool_schema = {
        "name": cmd_name,
        "description": cmd_info["summary"],
        "inputSchema": {
            "type": "object",
            "properties": {
                arg["name"]: {"type": arg["type"], "description": arg.get("doc", "")}
                for arg in cmd_info["args"] + cmd_info["options"]
            },
            "required": [arg["name"] for arg in cmd_info["args"]],
        },
    }

# Execute commands via MCP tool calls
def handle_tool_call(tool_name, arguments):
    try:
        result = client.command(tool_name, **arguments)
        return {"content": result}
    except IPAError as e:
        return e.to_dict()
```

## Testing

### CI Script

The project includes a CI script for code quality checks:

```bash
# Check code formatting (PEP8 compliance)
./contrib/ci.sh format

# Run linter
./contrib/ci.sh linter

# Run type checker
./contrib/ci.sh type

# Check shell scripts
./contrib/ci.sh shellcheck

# Run tests with coverage report
./contrib/ci.sh test

# Run all checks
./contrib/ci.sh all
```

### Unit Tests

```bash
pytest tests/test_ipaclient.py -v
```

### Integration Tests

Integration tests require a live IPA server. See [testing.md](docs/testing.md) for setup instructions.

```bash
# Skip integration tests (default)
pytest -v

# Run integration tests
pytest -m integration -v
```

### Coverage

```bash
pytest --cov=ipaclient --cov-report=term-missing --cov-report=html
# HTML report: htmlcov/index.html
```

## License

This project is licensed under the GNU General Public License v3.0. See [COPYING](COPYING) for details.

## Contributing

Contributions are welcome! Please read [contributing.md](docs/contributing.md) for detailed guidelines on licensing, sign-off requirements, AI-assisted contributions, and the contribution workflow.

**Quick Start:**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Install development dependencies (`pip install -e ".[dev]"`)
4. Set up pre-commit hooks (recommended - choose one):

   **Option 1: Using pre-commit**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

   **Option 2: Using prek**
   ```bash
   pip install prek
   prek install
   ```

5. Write tests for your changes
6. Ensure all checks pass (`./contrib/ci.sh all`)
7. Commit your changes with sign-off (`git commit --signoff`)
8. Push to the branch (`git push origin feature/my-feature`)
9. Open a Pull Request

### Pre-commit Hooks

The project uses pre-commit hooks to enforce code quality standards automatically before each commit. You can use either **pre-commit** or **prek** to manage these hooks.

The hooks run:

- **trailing-whitespace**: Remove trailing whitespace
- **end-of-file-fixer**: Ensure files end with a newline
- **check-added-large-files**: Prevent commits of large files (>100KB)
- **check-merge-conflict**: Detect merge conflict markers
- **shellcheck**: Lint shell scripts with the same configuration as CI

**Using pre-commit:**

```bash
pip install pre-commit
pre-commit install

# Run on all files
pre-commit run --all-files

# Run on staged files only
pre-commit run
```

**Using prek:**

```bash
pip install prek
prek install

# Run on all files
prek run --all-files

# Run on staged files only
prek run
```

Once installed, the hooks will run automatically on `git commit`.

All code must pass formatting, linting, type checking, shellcheck, and tests before merging.
