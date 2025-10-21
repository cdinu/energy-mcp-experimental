"""
Experimental Model Context Protocol (MCP) server for energy data exploration.

Includes unofficial integrations with Vaillant APIs and UK carbon intensity data.
"""

from energy_mcp_experimental.server import mcp, run  # noqa: F401

__all__ = ["mcp", "run"]
__version__ = "0.1.0"
