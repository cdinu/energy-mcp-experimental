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
  1. Locate `claude_desktop_config.json` (for example on macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`).
  2. Add or update an entry under `mcpServers` similar to:

     ```json
     {
       "mcpServers": {
         "energy-mcp-experimental": {
           "command": "uv",
           "args": [
             "run",
             "--directory",
             "/absolute/path/to/energy-mcp-experimental",
             "--project",
             "/absolute/path/to/energy-mcp-experimental",
             "energy-mcp"
           ],
           "env": {
             "VAILLANT_SERIAL": "xxxxxxxxxxx",
             "USER_POSTCODE": "DE1"
           }
         }
       }
     }
     ```

     Adjust the paths (and any environment variables) to match your setup. Claude Desktop launches the server over stdio automatically—no SSE flag is required.
  3. Restart Claude Desktop so the new configuration is picked up.

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

---

## Integrating With LLMs (MCP Clients)

The **Energy MCP Experimental** server can be consumed by any LLM client that speaks the [Model Context Protocol](https://modelcontextprotocol.io/). Below are examples showing integration with Anthropic’s API, Python `agents` library, Node.js, and curl.

### Anthropic (Python SDK)

```python
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1000,
    messages=[{
        "role": "user",
        "content": "Show me the current state of my Vaillant heat pump."
    }],
    mcp_servers=[{
        "type": "url",
        "url": "https://your-deployed-mcp-address:8000/mcp",
        "name": "vaillant-mcp",
        "authorization_token": "YOUR_TOKEN"
    }],
    betas=["mcp-client-2025-04-04"]
)
```

### Python Agents SDK (HTTP)

```python
import asyncio
import os

from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings

async def main() -> None:
    token = os.environ["MCP_SERVER_TOKEN"]
    async with MCPServerStreamableHttp(
        name="Vaillant MCP over HTTP",
        params={
            "url": "https://your-deployed-mcp-address:8000/mcp",
            "headers": {"Authorization": f"Bearer {token}"},
            "timeout": 10,
        },
        cache_tools_list=True,
        max_retry_attempts=3,
    ) as server:
        agent = Agent(
            name="Assistant",
            instructions="Use the Vaillant MCP tools to answer questions.",
            mcp_servers=[server],
            model_settings=ModelSettings(tool_choice="required"),
        )

        result = await Runner.run(agent, "Get the current carbon intensity forecast for SW1A 1AA.")
        print(result.final_output)

asyncio.run(main())
```

### Python Agents SDK (stdio)

```python
from pathlib import Path
from agents import Agent, Runner
from agents.mcp import MCPServerStdio

current_dir = Path(__file__).parent

async with MCPServerStdio(
    name="Vaillant MCP via stdio",
    params={
        "command": "uv",
        "args": ["run", "energy-mcp"],
    },
) as server:
    agent = Agent(
        name="Assistant",
        instructions="Use the Vaillant MCP tools to answer questions.",
        mcp_servers=[server],
    )
    result = await Runner.run(agent, "Retrieve my Vaillant heat pump settings.")
    print(result.final_output)
```

### curl

```bash
curl https://api.anthropic.com/v1/messages   -H "Content-Type: application/json"   -H "X-API-Key: $ANTHROPIC_API_KEY"   -H "anthropic-version: 2023-06-01"   -H "anthropic-beta: mcp-client-2025-04-04"   -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1000,
    "messages": [{"role": "user", "content": "Get the Vaillant system topology."}],
    "mcp_servers": [
      {
        "type": "url",
        "url": "https://your-deployed-mcp-address:8000/mcp",
        "name": "vaillant-mcp",
        "authorization_token": "YOUR_TOKEN"
      }
    ]
  }'
```

### Node.js (Anthropic SDK)

```javascript
import { Anthropic } from '@anthropic-ai/sdk';

const anthropic = new Anthropic();

const response = await anthropic.beta.messages.create({
  model: "claude-sonnet-4-5",
  max_tokens: 1000,
  messages: [
    {
      role: "user",
      content: "What is the latest energy consumption from my Vaillant heat pump?",
    },
  ],
  mcp_servers: [
    {
      type: "url",
      url: "https://your-deployed-mcp-address:8000/mcp",
      name: "vaillant-mcp",
      authorization_token: "YOUR_TOKEN",
    },
  ],
  betas: ["mcp-client-2025-04-04"],
});
```

---

## Development

```bash
uv pip install --editable .[dev]
pytest
```

## License

Released under the [MIT License](./LICENSE).
