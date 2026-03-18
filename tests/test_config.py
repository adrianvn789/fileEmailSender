"""Tests for config validation and exit codes."""
import subprocess
import sys


def test_missing_env_var_exits_2():
    """Running canva-client without .env exits with code 2."""
    result = subprocess.run(
        [sys.executable, "-m", "canva_client.cli"],
        capture_output=True,
        text=True,
        env={"PATH": ""},  # empty env — no vars set
    )
    assert result.returncode == 2


def test_missing_env_var_names_variable():
    """Exit message names the missing variable."""
    result = subprocess.run(
        [sys.executable, "-m", "canva_client.cli"],
        capture_output=True,
        text=True,
        env={"PATH": ""},
    )
    assert "required environment variable" in result.stderr
    assert "CANVA_CLIENT_ID" in result.stderr
