# SPDX-License-Identifier: GPL-3.0-or-later
import json

from mcp.types import Tool, ToolAnnotations

from .common import get_client, ipa_type_to_json_schema, to_api_name, to_cli_name

_SKIP_COMMANDS = {"ping"}


def is_read_only(api_name: str) -> bool:
    return "_find" in api_name or "_show" in api_name


def build_command_input_schema(cmd: dict) -> dict:
    properties: dict = {}
    required: list[str] = []

    for param in cmd["args"]:
        schema = {
            **ipa_type_to_json_schema(param["type"]),
            "description": param.get("doc", ""),
        }
        properties[param["name"]] = schema
        if param.get("required", True):
            required.append(param["name"])

    for param in cmd["options"]:
        schema = {
            **ipa_type_to_json_schema(param["type"]),
            "description": param.get("doc", ""),
        }
        if "default" in param:
            schema["default"] = param["default"]
        properties[param["name"]] = schema
        if param.get("required", False):
            required.append(param["name"])

    result: dict = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    return result


def build_tool(cmd: dict) -> Tool:
    api_name = cmd["name"]
    read_only = is_read_only(api_name)
    return Tool(
        name=to_cli_name(api_name),
        description=cmd.get("doc", cmd.get("summary", "")),
        inputSchema=build_command_input_schema(cmd),
        annotations=ToolAnnotations(
            readOnlyHint=read_only,
            destructiveHint=not read_only,
            idempotentHint=read_only,
        ),
    )


def build_all_tools() -> tuple[list[Tool], dict[str, dict]]:
    """Return (Tool list, {cli_name: cmd_dict}) from the live server schema."""
    client = get_client()
    schema = client.export_schema()
    tools: list[Tool] = []
    cmd_schemas: dict[str, dict] = {}
    for api_name, cmd in schema.get("commands", {}).items():
        cli_name = to_cli_name(api_name)
        if cli_name in _SKIP_COMMANDS:
            continue
        tools.append(build_tool(cmd))
        cmd_schemas[cli_name] = cmd
    return tools, cmd_schemas


def execute_command(cli_name: str, arguments: dict, cmd_schema: dict) -> str:
    """Execute a dynamic IPA command and return pretty-printed JSON."""
    api_name = to_api_name(cli_name)
    arg_names = {a["name"] for a in cmd_schema["args"]}
    positional = [
        arguments[a["name"]] for a in cmd_schema["args"] if a["name"] in arguments
    ]
    options = {k: v for k, v in arguments.items() if k not in arg_names}
    client = get_client()
    result = client.command(api_name, *positional, **options)
    return json.dumps(result, indent=2, default=str)
