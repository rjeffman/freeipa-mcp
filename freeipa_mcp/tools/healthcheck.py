# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import json
import subprocess


def _get_kerberos_principal() -> str:
    result = subprocess.run(["klist"], capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError("No Kerberos ticket found. Run the login tool first.")
    for line in result.stdout.splitlines():
        if line.startswith("Default principal:"):
            return line.split(":", 1)[1].strip().split("@")[0]
    raise RuntimeError("Could not parse Kerberos principal from klist output")


def _exec_ssh(
    hostname: str, username: str, command: str, password: str | None = None
) -> str:
    escaped_cmd = command.replace("\\", "\\\\").replace('"', '\\"')
    if password is not None:
        escaped_pwd = password.replace("\\", "\\\\").replace("'", "'\\''")
        remote = (
            f"bash -c \"cd / && sudo --stdin {escaped_cmd} <<< '{escaped_pwd}'"
            f'; echo $?"'
        )
    else:
        remote = f'bash -c "cd / && sudo {escaped_cmd}; echo $?"'

    result = subprocess.run(
        [
            "ssh",
            "-T",
            "-o", "GSSAPIAuthentication=yes",
            "-o", "GSSAPIDelegateCredentials=yes",
            "-o", "StrictHostKeyChecking=accept-new",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=30",
            f"{username}@{hostname}",
            remote,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    stdout_lines = result.stdout.splitlines()
    if stdout_lines:
        try:
            exit_code = int(stdout_lines[-1])
            output = "\n".join(stdout_lines[:-1])
        except ValueError:
            exit_code = result.returncode
            output = result.stdout
    else:
        exit_code = result.returncode
        output = result.stdout

    stderr = result.stderr.strip()
    if exit_code != 0:
        if "incorrect password" in stderr.lower() or "sorry" in stderr.lower():
            raise RuntimeError("sudo authentication failed: incorrect password")
        if "not in the sudoers" in stderr.lower():
            raise RuntimeError(
                f"User {username} is not permitted to run sudo on {hostname}"
            )
        raise RuntimeError(
            f"Remote command failed (exit {exit_code}): {stderr or output}"
        )
    return output


_SNAKE_SPECIAL: dict[str, str] = {
    "msg": "Message",
    "ca": "CA",
    "dns": "DNS",
    "ntp": "NTP",
    "url": "URL",
    "uri": "URI",
    "uuid": "UUID",
    "id": "ID",
}


def _snake_to_title(s: str) -> str:
    if s.lower() in _SNAKE_SPECIAL:
        return _SNAKE_SPECIAL[s.lower()]
    parts = []
    for word in s.split("_"):
        parts.append(_SNAKE_SPECIAL.get(word.lower(), word.capitalize()))
    return " ".join(parts)


def _format_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(_format_value(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, separators=(",", ":"))
    if value is None:
        return "null"
    return str(value)


def _format_kw(kw: dict) -> str:
    if not kw:
        return "*(No additional details)*\n"
    lines = []
    for key, value in kw.items():
        lines.append(f"- **{_snake_to_title(key)}:** {_format_value(value)}")
    return "\n".join(lines) + "\n"


def _format_entry(entry: dict) -> str:
    source = entry.get("source", "")
    check = entry.get("check", "")
    result = entry.get("result", "")
    kw = entry.get("kw", {})
    return (
        f"### {source} - {check}\n\n"
        f"**Status:** {result}\n\n"
        f"{_format_kw(kw)}"
        "\n---\n\n"
    )


def _generate_summary(grouped: dict[str, list]) -> str:
    total = sum(len(v) for v in grouped.values())
    critical = len(grouped.get("CRITICAL", []))
    errors = len(grouped.get("ERROR", []))
    warnings = len(grouped.get("WARNING", []))
    success = len(grouped.get("SUCCESS", []))

    lines = [
        "## Summary",
        f"- **Total Checks:** {total}",
        f"- **Critical:** {critical} \U0001f534",
        f"- **Errors:** {errors} \U0001f7e0",
        f"- **Warnings:** {warnings} \U0001f7e1",
        f"- **Success:** {success} \U0001f7e2",
        "",
    ]
    if critical > 0 or errors > 0:
        lines.append("**Overall Status:** Issues found that require attention")
    elif warnings > 0:
        lines.append("**Overall Status:** Minor issues detected")
    else:
        lines.append("**Overall Status:** All checks passed \u2705")
    return "\n".join(lines)


def _format_as_markdown(json_output: str) -> str:
    try:
        results = json.loads(json_output)
    except json.JSONDecodeError:
        return json_output
    if not isinstance(results, list):
        return json_output

    if not results:
        return "# IPA Healthcheck Results\n\nNo healthcheck results found.\n"

    grouped: dict[str, list] = {}
    for item in results:
        grouped.setdefault(item.get("result", "UNKNOWN"), []).append(item)

    out = "# IPA Healthcheck Results\n\n"
    out += _generate_summary(grouped) + "\n"

    for sev in ["CRITICAL", "ERROR", "WARNING", "SUCCESS"]:
        entries = grouped.get(sev, [])
        if entries:
            out += f"## {sev} Results\n\n"
            for entry in entries:
                out += _format_entry(entry)

    if grouped.get("CRITICAL") or grouped.get("ERROR") or grouped.get("WARNING"):
        out += (
            "## Recommendations\n\n"
            "Review the issues above and take appropriate action:\n"
            "1. Address CRITICAL and ERROR items immediately\n"
            "2. Plan fixes for WARNING items\n"
            "3. Re-run healthcheck after making changes to verify fixes\n\n"
            "For more information, see:"
            " https://www.freeipa.org/page/Troubleshooting\n"
        )

    return out


def _healthcheck_blocking(
    server_hostname: str,
    username: str,
    mode: str,
    source: str | None,
    check: str | None,
    failures_only: bool,
    severity: list[str] | None,
    password: str | None,
    output_format: str,
) -> str:
    if mode == "log":
        cmd = "cat /var/log/ipa/healthcheck/healthcheck.log"
        output = _exec_ssh(server_hostname, username, cmd, password)
    else:
        parts = ["ipa-healthcheck", "--output-type", "json"]
        if source:
            parts += ["--source", source]
        if check:
            parts += ["--check", check]
        if failures_only:
            parts.append("--failures-only")
        if severity:
            for s in severity:
                parts += ["--severity", s]
        output = _exec_ssh(server_hostname, username, " ".join(parts), password)

    if output_format == "json":
        return output
    return _format_as_markdown(output)


async def execute(
    server_hostname: str,
    mode: str = "live",
    source: str | None = None,
    check: str | None = None,
    failures_only: bool = False,
    severity: list[str] | None = None,
    passwordless: bool = False,
    output_format: str = "markdown",
) -> str:
    username = await asyncio.to_thread(_get_kerberos_principal)

    password: str | None = None
    if not passwordless:
        from .sudo_gui import get_sudo_password
        password = await asyncio.to_thread(get_sudo_password, username, server_hostname)

    return await asyncio.to_thread(
        _healthcheck_blocking,
        server_hostname, username, mode, source, check,
        failures_only, severity, password, output_format,
    )
