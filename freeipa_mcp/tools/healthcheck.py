# SPDX-License-Identifier: GPL-3.0-or-later
import asyncio
import json
import subprocess

try:
    import paramiko
    _HAS_PARAMIKO = True
except ImportError:
    _HAS_PARAMIKO = False


def _get_kerberos_principal() -> str:
    result = subprocess.run(["klist"], capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise RuntimeError("No Kerberos ticket found. Run the login tool first.")
    for line in result.stdout.splitlines():
        if line.startswith("Default principal:"):
            return line.split(":", 1)[1].strip().split("@")[0]
    raise RuntimeError("Could not parse Kerberos principal from klist output")


def _exec_ssh(
    hostname: str, username: str, command: str, sudo_password: str | None
) -> str:
    if not _HAS_PARAMIKO:
        raise RuntimeError(
            "paramiko is required for healthcheck. Install with: pip install paramiko"
        )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname, username=username,
            gss_auth=True, gss_kex=True, gss_deleg_creds=True, timeout=30,
        )
        if sudo_password:
            cmd_str = f"sudo -S sh -c {repr(command)}"
            stdin, stdout, stderr = client.exec_command(cmd_str)
            stdin.write(sudo_password + "\n")
            stdin.flush()
            stdin.channel.shutdown_write()
        else:
            stdin, stdout, stderr = client.exec_command(f"sudo sh -c {repr(command)}")
        output = stdout.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        err = stderr.read().decode()
        if exit_code != 0:
            raise RuntimeError(f"SSH command failed (exit {exit_code}): {err.strip()}")
        return output
    finally:
        client.close()


def _format_as_markdown(json_output: str) -> str:
    try:
        results = json.loads(json_output)
    except json.JSONDecodeError:
        return json_output
    if not isinstance(results, list):
        return json_output

    counts: dict[str, int] = {"SUCCESS": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
    for item in results:
        sev = item.get("severity", "UNKNOWN")
        if sev in counts:
            counts[sev] += 1

    lines = [
        "# IPA Healthcheck Results\n",
        f"**Total:** {len(results)} | **Critical:** {counts['CRITICAL']} | "
        f"**Error:** {counts['ERROR']} | **Warning:** {counts['WARNING']} | "
        f"**Success:** {counts['SUCCESS']}\n",
    ]
    by_severity: dict[str, list] = {}
    for item in results:
        by_severity.setdefault(item.get("severity", "UNKNOWN"), []).append(item)

    for sev in ["CRITICAL", "ERROR", "WARNING", "SUCCESS"]:
        if sev not in by_severity:
            continue
        lines.append(f"\n## {sev}\n")
        for item in by_severity[sev]:
            lines.append(f"- **{item.get('source', '')}** / {item.get('check', '')}")
            for k, v in item.get("kw", {}).items():
                lines.append(f"  - {k}: {v}")
    return "\n".join(lines)


def _healthcheck_blocking(
    server_hostname: str,
    mode: str,
    source: str | None,
    check: str | None,
    failures_only: bool,
    severity: list[str] | None,
    passwordless: bool,
    output_format: str,
) -> str:
    username = _get_kerberos_principal()

    if mode == "log":
        cmd = "cat /var/log/ipa/healthcheck/healthcheck.log"
        output = _exec_ssh(server_hostname, username, cmd, None)
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
        cmd = " ".join(parts)
        if not passwordless:
            raise ValueError(
                "Non-passwordless sudo requires GUI support. "
                "Set passwordless=True with appropriate sudoers configuration."
            )
        output = _exec_ssh(server_hostname, username, cmd, None)

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
    return await asyncio.to_thread(
        _healthcheck_blocking,
        server_hostname, mode, source, check,
        failures_only, severity, passwordless, output_format,
    )
