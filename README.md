# Energy MCP Experimental

An **experimental** [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that combines:

- Unofficial access to Vaillant Group energy data via the companion [`vaillant-client`](https://github.com/cdinu/vaillant-client) library.
- UK National Grid carbon intensity forecasts from [carbonintensity.org.uk](https://carbonintensity.org.uk/).

> **Important:** This project is carried out by Cristian Dinu for research and tinkering purposes. It is **not affiliated with or endorsed by Vaillant** and ships without official support. Expect rough edges and breaking changes.

## Status & Limitations

- Alpha-quality, public, open source.
- Intended for local experimentation only – deploy behind your own firewall.
- Vaillant support depends on environment variables (`VAILLANT_API_*` and `VAILLANT_SERIAL`) and currently reads a **single hard-coded serial number** from the environment.
- No secrets or serial numbers are included; you must supply your own credentials.
- Some Vaillant endpoints remain incomplete; errors are surfaced as user-friendly messages where possible.

## Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) for dependency management (recommended).
- Access to the Vaillant developer portal: https://developer.vaillant-group.com/
- Credentials for the Vaillant APIs plus the serial number of your system stored locally (e.g., in a `.env` file).

## Installation

```bash
# Clone the repository
git clone https://github.com/cdinu/energy-mcp-experimental.git
cd energy-mcp-experimental

# Install dependencies with uv
uv pip sync uv.lock

# (Optional) pull in the Vaillant extras directly from GitHub
uv pip sync --extra vaillant uv.lock

# (Recommended) install the experimental Vaillant client
uv pip install --editable ../vaillant-client  # adjust path as needed
```

Populate a local `.env` (ignored by git) with the required secrets:

```ini
VAILLANT_API_CLIENT=your-client-id
VAILLANT_API_SECRET=your-client-secret
VAILLANT_API_SUBSCRIBTION_KEY=your-subscription-key
VAILLANT_API_DIAGNOSTIC_SUBSCRIBTION_KEY=your-diagnostics-key
VAILLANT_API_CONTRACT_NUMBER=your-contract
VAILLANT_SERIAL=your-serial-number
USER_POSTCODE=SW1A 1AA  # optional, used for carbon intensity tools
```

## Running The Server

Start the server over stdio (useful for editors and terminals):

```bash
uv run energy-mcp
```

For SSE transport (required by Claude Desktop), leverage the module entry point:

```bash
uv run python -m energy_mcp_experimental sse
```

Logs are written to `energy-mcp-*.log` in the working directory for troubleshooting.

## MCP Client Setup

- **Claude Desktop**
  1. Launch Claude Desktop and open **Settings → Developer**.
  2. Add a new MCP Server with:
     - **Command:** `uv`
     - **Arguments:** `run python -m energy_mcp_experimental sse`
     - **Directory:** Path to your `energy-mcp-experimental` checkout.
  3. Ensure your `.env` file is loaded before starting Claude. When running, Claude will connect over SSE to the local server.

- **VS Code (Claude or Cursor extensions)**
  1. Install the MCP-capable extension.
  2. In the extension settings, add a new local MCP server configuration pointing to:
     - Command: `uv`
     - Args: `run energy-mcp`
     - Working directory: repository root.
  3. Restart the editor so the extension can spawn the server via stdio.

## Available Tools

- `vaillant_energy_consumption` — Aggregated and per-period energy usage in friendly tabular form.
- `vaillant_advanced_diagnostics` — Detailed diagnostics, masking serial numbers for privacy.
- `vaillant_get_topology` — System topology and device metadata.
- `vaillant_get_settings` — Current system settings including schedules and overrides.
- `vaillant_get_state` — Live system state data.
- `current_uk_grid_carbon_intensity_in_postcode` — Regional carbon intensity snapshot (requires `USER_POSTCODE` or parameter).
- `carbon_intensity_history_and_forecast_for_postcode` — Local forecast for the next 24–48 hours.
- `carbon_intensity_history_and_forecast_national` — National-level forecast with tabular output.
- `current_national_generation_mix` — Fuel mix for UK electricity generation right now.

The Vaillant tools will respond with a helpful warning if the `vaillant-client` dependency is missing.

## Development

```bash
uv pip install --editable .[dev]
pytest
```

## License

Released under the [MIT License](./LICENSE).
