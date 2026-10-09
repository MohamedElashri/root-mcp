"""Package and CLI versions must follow installed distribution metadata."""

import json
from importlib.metadata import version

import pytest
from click.testing import CliRunner

import root_cli
import root_mcp
from root_cli.main import cli
from root_mcp.config import ServerConfig


def test_public_versions_match_distribution() -> None:
    expected = version("root-mcp")

    assert root_mcp.__version__ == expected
    assert root_cli.__version__ == expected
    assert ServerConfig().version == expected


@pytest.mark.parametrize("arguments", [["--version"], ["info"], ["--json", "info"]])
def test_cli_reports_distribution_version(arguments: list[str], monkeypatch) -> None:
    # Version reporting should also work without loading the analysis backend.
    monkeypatch.setattr("root_cli.main.get_backend_status", lambda: False)
    result = CliRunner().invoke(cli, arguments)

    assert result.exit_code == 0
    expected = version("root-mcp")
    if "--json" in arguments:
        assert json.loads(result.stdout)["version"] == expected
    else:
        assert expected in result.stdout
