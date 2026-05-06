# SPDX-License-Identifier: GPL-3.0-or-later
"""
Tests for file path validation security.

Covers:
- Path traversal attack prevention
- Symlink attack prevention
- Home directory constraint enforcement
"""

import os
from pathlib import Path

import pytest

from freeipa_mcp.tools.common import validate_file_path


@pytest.fixture
def temp_home(monkeypatch, tmp_path):
    """Create a temporary home directory for testing."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    return home


def test_validate_file_path_accepts_file_in_home(temp_home):
    """Valid file under home directory should be accepted."""
    test_file = temp_home / "test.txt"
    test_file.write_text("content")

    result = validate_file_path(test_file, allow_write=False)
    assert result == test_file.resolve()


def test_validate_file_path_accepts_subdirectory_file(temp_home):
    """Valid file in subdirectory should be accepted."""
    subdir = temp_home / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_file.write_text("content")

    result = validate_file_path(test_file, allow_write=False)
    assert result == test_file.resolve()


def test_validate_file_path_accepts_relative_path(temp_home):
    """Relative path under home should be accepted."""
    test_file = temp_home / "test.txt"
    test_file.write_text("content")

    # Change to home directory
    os.chdir(temp_home)
    result = validate_file_path("test.txt", allow_write=False)
    assert result == test_file.resolve()


def test_validate_file_path_rejects_absolute_outside_home(temp_home):
    """Absolute path outside home directory should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/etc/shadow", allow_write=False)


def test_validate_file_path_rejects_relative_traversal_outside_home(temp_home):
    """Path traversal using ../ outside home should be rejected."""
    subdir = temp_home / "subdir"
    subdir.mkdir()
    os.chdir(subdir)

    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("../../etc/shadow", allow_write=False)


def test_validate_file_path_rejects_etc_shadow(temp_home):
    """Attempt to read /etc/shadow should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/etc/shadow", allow_write=False)


def test_validate_file_path_rejects_etc_passwd(temp_home):
    """Attempt to read /etc/passwd should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/etc/passwd", allow_write=False)


def test_validate_file_path_rejects_root_ssh_keys(temp_home):
    """Attempt to read root's SSH keys should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/root/.ssh/id_rsa", allow_write=False)


def test_validate_file_path_rejects_write_to_etc(temp_home):
    """Attempt to write to /etc should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/etc/cron.d/backdoor", allow_write=True)


def test_validate_file_path_rejects_write_to_tmp_outside_home(temp_home):
    """Attempt to write to /tmp should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/tmp/exploit", allow_write=True)  # noqa: S108


def test_validate_file_path_rejects_symlink_to_outside_home(temp_home):
    """Symlink pointing outside home should be rejected."""
    link = temp_home / "link_to_shadow"
    link.symlink_to("/etc/shadow")

    # Symlink resolves to /etc/shadow which is outside home
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path(link, allow_write=False)


def test_validate_file_path_rejects_symlink_in_parent_to_outside(temp_home):
    """Symlink in parent directory pointing outside should be rejected."""
    # Create: home/malicious_link -> /etc
    malicious_link = temp_home / "malicious_link"
    malicious_link.symlink_to("/etc")

    # Try to access: home/malicious_link/shadow (resolves to /etc/shadow)
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path(malicious_link / "shadow", allow_write=False)


def test_validate_file_path_accepts_symlink_within_home(temp_home):
    """Symlink pointing to another location within home should be accepted."""
    target = temp_home / "target.txt"
    target.write_text("content")

    link = temp_home / "link.txt"
    link.symlink_to(target)

    result = validate_file_path(link, allow_write=False)
    # Should resolve to target location, which is still in home
    assert result == target.resolve()


def test_validate_file_path_accepts_relative_symlink_within_home(temp_home):
    """Relative symlink within home should be accepted."""
    subdir = temp_home / "subdir"
    subdir.mkdir()

    target = subdir / "target.txt"
    target.write_text("content")

    link = subdir / "link.txt"
    link.symlink_to("target.txt")  # Relative symlink

    result = validate_file_path(link, allow_write=False)
    assert result == target.resolve()


def test_validate_file_path_read_mode_requires_file_exists(temp_home):
    """Read mode should reject non-existent files."""
    nonexistent = temp_home / "does_not_exist.txt"

    with pytest.raises(FileNotFoundError, match="File not found"):
        validate_file_path(nonexistent, allow_write=False)


def test_validate_file_path_write_mode_allows_nonexistent_file(temp_home):
    """Write mode should allow non-existent files if parent exists."""
    new_file = temp_home / "new_file.txt"
    assert not new_file.exists()

    result = validate_file_path(new_file, allow_write=True)
    assert result == new_file.resolve()


def test_validate_file_path_write_mode_requires_parent_exists(temp_home):
    """Write mode should reject if parent directory doesn't exist."""
    new_file = temp_home / "nonexistent_dir" / "new_file.txt"

    with pytest.raises(ValueError, match="Parent directory does not exist"):
        validate_file_path(new_file, allow_write=True)


def test_validate_file_path_write_mode_allows_file_in_existing_subdir(temp_home):
    """Write mode should allow new file in existing subdirectory."""
    subdir = temp_home / "subdir"
    subdir.mkdir()
    new_file = subdir / "new_file.txt"

    result = validate_file_path(new_file, allow_write=True)
    assert result == new_file.resolve()


def test_validate_file_path_accepts_string_path(temp_home):
    """Function should accept string paths."""
    test_file = temp_home / "test.txt"
    test_file.write_text("content")

    result = validate_file_path(str(test_file), allow_write=False)
    assert result == test_file.resolve()


def test_validate_file_path_accepts_path_object(temp_home):
    """Function should accept Path objects."""
    test_file = temp_home / "test.txt"
    test_file.write_text("content")

    result = validate_file_path(test_file, allow_write=False)
    assert result == test_file.resolve()


def test_validate_file_path_rejects_dev_null(temp_home):
    """Attempt to use /dev/null should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/dev/null", allow_write=True)


def test_validate_file_path_rejects_proc_files(temp_home):
    """Attempt to read /proc files should be rejected."""
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("/proc/self/environ", allow_write=False)


def test_validate_file_path_handles_tilde_expansion(temp_home):
    """Paths with ~ should be handled correctly."""
    test_file = temp_home / "test.txt"
    test_file.write_text("content")

    # Manually expand ~ since we've mocked Path.home()
    path_str = str(test_file).replace(str(temp_home), "~")
    expanded = path_str.replace("~", str(temp_home))

    result = validate_file_path(expanded, allow_write=False)
    assert result == test_file.resolve()


def test_validate_file_path_complex_traversal_attack(temp_home):
    """Complex path traversal attack should be blocked."""
    subdir = temp_home / "a" / "b" / "c"
    subdir.mkdir(parents=True)
    os.chdir(subdir)

    # Try to escape using multiple ../
    with pytest.raises(ValueError, match="must be under home directory"):
        validate_file_path("../../../../etc/shadow", allow_write=False)


def test_validate_file_path_double_slash_normalization(temp_home):
    """Paths with double slashes should be normalized correctly."""
    test_file = temp_home / "test.txt"
    test_file.write_text("content")

    # Path with double slashes
    path_with_double = str(test_file).replace("/", "//", 1)

    result = validate_file_path(path_with_double, allow_write=False)
    assert result == test_file.resolve()
