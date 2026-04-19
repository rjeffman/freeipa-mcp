# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import json
import logging
from pathlib import Path

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool, ToolAnnotations

from .tools import create_ipaconf, dynamic, healthcheck, login, ping
from .tools import help as help_tool
from .tools.common import to_api_name

logger = logging.getLogger(__name__)

app = Server("freeipa-mcp")

_dynamic_tools: list[Tool] = []
_dynamic_cmd_schemas: dict[str, dict] = {}

# --- Static tool definitions ---

PING_TOOL = Tool(
    name="ping",
    description=(
        "Ping the FreeIPA server to check connectivity "
        "and retrieve version information."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "ipa_confdir": {
                "type": "string",
                "description": "Ignored; kept for API compatibility",
            },
        },
        "additionalProperties": False,
    },
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True
    ),
)

HELP_TOOL = Tool(
    name="help",
    description=(
        "Get FreeIPA help. Set subject to 'topics' to list topics, "
        "'commands' to list all "
        "commands, or a specific topic/command name for full markdown documentation. "
        "Examples: subject='topics', subject='user', subject='user-add'."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "subject": {
                "type": "string",
                "description": (
                    "The help subject: 'topics', 'commands', or a topic/command name"
                ),
            },
            "ipa_confdir": {
                "type": "string",
                "description": "Ignored; kept for API compatibility",
            },
            "force_refresh": {
                "type": "boolean",
                "description": "Force regeneration of cached documentation",
                "default": False,
            },
        },
        "required": ["subject"],
        "additionalProperties": False,
    },
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True
    ),
)

CREATE_IPACONF_TOOL = Tool(
    name="create_ipaconf",
    description=(
        "Configure the FreeIPA server connection. Validates the server FQDN, "
        "downloads and caches the CA certificate, verifies connectivity, "
        "and automatically "
        "loads all available IPA commands as MCP tools."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "server_hostname": {
                "type": "string",
                "description": (
                    "The FQDN of the FreeIPA server (e.g., ipa.demo1.freeipa.org)"
                ),
            },
            "realm": {
                "type": "string",
                "description": (
                    "The Kerberos realm (optional, derived from server_hostname)"
                ),
            },
            "domain": {
                "type": "string",
                "description": "The DNS domain (optional, derived from realm)",
            },
        },
        "required": ["server_hostname"],
        "additionalProperties": False,
    },
)

LOGIN_TOOL = Tool(
    name="login",
    description=(
        "Authenticate to a Kerberos realm to obtain a Ticket-Granting Ticket (TGT). "
        "Provide username and password for non-interactive authentication. "
        "The realm is auto-detected from the saved server "
        "configuration if not provided."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "username": {
                "type": "string",
                "description": "Username or full principal (user@REALM)",
            },
            "password": {
                "type": "string",
                "description": "Password for authentication",
            },
            "realm": {
                "type": "string",
                "description": "Kerberos realm (auto-detected if omitted)",
            },
            "renewable_lifetime": {
                "type": "string",
                "description": "Ticket renewable lifetime (e.g., '7d')",
                "default": "7d",
            },
            "ipa_confdir": {
                "type": "string",
                "description": "Ignored; kept for API compatibility",
            },
        },
        "additionalProperties": False,
    },
)

HEALTHCHECK_TOOL = Tool(
    name="healthcheck",
    description=(
        "Execute IPA healthcheck on a remote server via SSH (Kerberos auth). "
        "Requires a valid Kerberos ticket and passwordless sudo on the target server."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "server_hostname": {
                "type": "string",
                "description": "FQDN of the IPA server to check",
            },
            "mode": {
                "type": "string",
                "enum": ["live", "log"],
                "description": "Run live healthcheck or read existing log file",
                "default": "live",
            },
            "source": {
                "type": "string",
                "description": "Specific healthcheck source to run",
            },
            "check": {
                "type": "string",
                "description": "Specific check to run (requires source)",
            },
            "failures_only": {
                "type": "boolean",
                "description": "Report only failures",
                "default": False,
            },
            "severity": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter by severity (SUCCESS, WARNING, ERROR, CRITICAL)",
            },
            "passwordless": {
                "type": "boolean",
                "description": "Use passwordless sudo",
                "default": False,
            },
            "output_format": {
                "type": "string",
                "enum": ["markdown", "json"],
                "description": "Output format",
                "default": "markdown",
            },
            "ipa_confdir": {
                "type": "string",
                "description": "Ignored; kept for API compatibility",
            },
        },
        "required": ["server_hostname"],
        "additionalProperties": False,
    },
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, idempotentHint=True
    ),
)

LOAD_TOOLS_TOOL = Tool(
    name="load_tools",
    description=(
        "Reload all available FreeIPA commands as MCP tools from the server schema. "
        "Automatically called by create_ipaconf. Also updates .claude/settings.json "
        "with allowedTools entries for all *-find and *-show commands."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "ipa_confdir": {
                "type": "string",
                "description": "Ignored; kept for API compatibility",
            },
        },
        "additionalProperties": False,
    },
)

STATIC_TOOLS = [
    PING_TOOL,
    HELP_TOOL,
    CREATE_IPACONF_TOOL,
    LOGIN_TOOL,
    HEALTHCHECK_TOOL,
    LOAD_TOOLS_TOOL,
]


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return STATIC_TOOLS + _dynamic_tools


async def _load_dynamic_tools() -> int:
    global _dynamic_tools, _dynamic_cmd_schemas
    tools, schemas = await asyncio.to_thread(dynamic.build_all_tools)
    _dynamic_tools = tools
    _dynamic_cmd_schemas = schemas
    return len(tools)


def _update_allowed_tools() -> None:
    read_only_names = [
        f"mcp__freeipa-mcp__{t.name}"
        for t in _dynamic_tools
        if dynamic.is_read_only(to_api_name(t.name))
    ]
    settings_path = Path(".claude/settings.json")
    settings: dict = {}
    if settings_path.exists():
        settings = json.loads(settings_path.read_text())
    existing = set(settings.get("allowedTools", []))
    existing.update(read_only_names)
    settings["allowedTools"] = sorted(existing)
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2))
    logger.info("Added %d allowed tools to .claude/settings.json", len(read_only_names))


async def _dispatch_tool(name: str, args: dict) -> str:
    try:
        if name == "ping":
            return await ping.execute(args.get("ipa_confdir"))
        if name == "help":
            return await help_tool.execute(
                subject=args["subject"],
                ipa_confdir=args.get("ipa_confdir"),
                force_refresh=args.get("force_refresh", False),
            )
        if name == "create_ipaconf":
            result = await create_ipaconf.execute(
                server_hostname=args["server_hostname"],
                realm=args.get("realm"),
                domain=args.get("domain"),
            )
            count = await _load_dynamic_tools()
            _update_allowed_tools()
            try:
                await app.request_context.session.send_tool_list_changed()
            except Exception:
                pass
            return result + f"\n{count} IPA commands loaded as MCP tools."
        if name == "login":
            return await login.execute(
                username=args.get("username"),
                password=args.get("password"),
                realm=args.get("realm"),
                renewable_lifetime=args.get("renewable_lifetime", "7d"),
                ipa_confdir=args.get("ipa_confdir"),
            )
        if name == "healthcheck":
            return await healthcheck.execute(
                server_hostname=args["server_hostname"],
                mode=args.get("mode", "live"),
                source=args.get("source"),
                check=args.get("check"),
                failures_only=args.get("failures_only", False),
                severity=args.get("severity"),
                passwordless=args.get("passwordless", False),
                output_format=args.get("output_format", "markdown"),
            )
        if name == "load_tools":
            count = await _load_dynamic_tools()
            _update_allowed_tools()
            try:
                await app.request_context.session.send_tool_list_changed()
            except Exception:
                pass
            return (
                f"Loaded {count} IPA commands as MCP tools.\n"
                "Read-only tools (*-find, *-show) added to "
                ".claude/settings.json allowedTools."
            )
        if name in _dynamic_cmd_schemas:
            return await asyncio.to_thread(
                dynamic.execute_command, name, args, _dynamic_cmd_schemas[name]
            )
        return f"Error: Unknown tool '{name}'"
    except Exception as exc:
        logger.error("Tool '%s' failed: %s", name, exc)
        return f"Error: {exc}"


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[TextContent]:
    result = await _dispatch_tool(name, arguments or {})
    return [TextContent(type="text", text=result)]


async def serve() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler()],
    )
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="freeipa-mcp",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(tools_changed=True),
                    experimental_capabilities={},
                ),
            ),
        )
