import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

import energy_mcp_experimental
from mcp.server.fastmcp import FastMCP
from energy_mcp_experimental.servers import vaillant as vaillant_server


def test_package_imports_and_version() -> None:
    assert hasattr(energy_mcp_experimental, "__version__")
    assert isinstance(energy_mcp_experimental.__version__, str)
    assert energy_mcp_experimental.__version__


def test_mcp_server_is_configured() -> None:
    server = energy_mcp_experimental.mcp
    assert isinstance(server, FastMCP)
    assert server.name == "Energy MCP Experimental"


def test_vaillant_dependency_message_when_client_missing() -> None:
    message = vaillant_server.vaillant_energy_consumption(
        "2025-01-01",
        "2025-01-02",
        "daily",
    )
    assert message.startswith(vaillant_server._VAILLANT_DEPENDENCY_MESSAGE)
