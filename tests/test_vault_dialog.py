# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for vault dialog security."""

from unittest.mock import MagicMock, patch

from freeipa_mcp.tools._vault_dialog import display_vault_data


def test_display_vault_data_passes_data_via_stdin_not_argv():
    """
    Security test: verify vault data is passed via stdin, not command-line args.

    CRITICAL: Command-line arguments are visible in process table via ps/proc.
    Sensitive vault data MUST be passed via stdin to prevent exposure.
    """
    vault_name = "test-vault"
    sensitive_data = b"secret password 123"

    with patch("subprocess.run") as mock_run:
        # Mock successful subprocess execution
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        # Call the function
        display_vault_data(vault_name, sensitive_data)

        # Verify subprocess.run was called
        assert mock_run.called
        call_args = mock_run.call_args

        # Check that command-line arguments do NOT contain the sensitive data
        cmd = call_args[0][0]  # First positional argument is the command list
        # Command should only have: [python, script_path, vault_name]
        # NOT the data!
        assert len(cmd) == 3, (
            f"Expected 3 args (python, script, vault_name), got {len(cmd)}: {cmd}"
        )
        assert vault_name in cmd, "vault_name should be in command args"

        # Verify data is NOT in any command-line argument
        for arg in cmd:
            assert b"secret" not in str(arg).encode()
            assert b"password" not in str(arg).encode()

        # Verify data IS passed via stdin
        kwargs = call_args[1]  # Keyword arguments
        assert "input" in kwargs, "Data should be passed via 'input' parameter (stdin)"
        assert kwargs["input"] == sensitive_data, (
            "stdin should contain the sensitive data"
        )
