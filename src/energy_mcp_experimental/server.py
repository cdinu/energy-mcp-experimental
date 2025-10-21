import datetime
import functools
import logging
import os
import sys
import time
from typing import Literal

from mcp.server.fastmcp import FastMCP

from energy_mcp_experimental.servers.carbonintensity import (
    carbon_intensity_history_and_forecast_for_postcode,
    carbon_intensity_history_and_forecast_national,
    current_national_generation_mix,
    current_uk_grid_carbon_intensity_in_postcode,
)
from energy_mcp_experimental.servers.vaillant import (
    vaillant_advanced_diagnostics,
    vaillant_energy_consumption,
    vaillant_get_settings,
    vaillant_get_state,
    vaillant_get_topology,
)


# Configure logging
def setup_logging():
    """Set up logging to file and console."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    pid = os.getpid()
    log_filename = f"energy-mcp-{timestamp}-{pid}.log"

    # Create a logger
    logger = logging.getLogger("energy_mcp_experimental")
    logger.setLevel(logging.INFO)

    # Create handlers
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.INFO)

    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)

    logger.info(f"Logging initialized. Log file: {log_filename}")
    return logger


# Set up logging
logger = setup_logging()


# Function decorator for logging
def log_function_call(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Calling {func.__name__} with args: {args}, kwargs: {kwargs}")
        try:
            result = func(*args, **kwargs)
            exec_time = time.time() - start_time
            logger.info(f"Function {func.__name__} completed in {exec_time:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            raise

    return wrapper


# Apply logging decorator to all server functions
vaillant_energy_consumption = log_function_call(vaillant_energy_consumption)
vaillant_advanced_diagnostics = log_function_call(vaillant_advanced_diagnostics)
vaillant_get_topology = log_function_call(vaillant_get_topology)
vaillant_get_settings = log_function_call(vaillant_get_settings)
vaillant_get_state = log_function_call(vaillant_get_state)

current_uk_grid_carbon_intensity_in_postcode = log_function_call(
    current_uk_grid_carbon_intensity_in_postcode
)
carbon_intensity_history_and_forecast_for_postcode = log_function_call(
    carbon_intensity_history_and_forecast_for_postcode
)
carbon_intensity_history_and_forecast_national = log_function_call(
    carbon_intensity_history_and_forecast_national
)
current_national_generation_mix = log_function_call(current_national_generation_mix)

# Create MCP instance
mcp = FastMCP("Energy MCP Experimental", "0.1.0")
logger.info(f"MCP instance created: {mcp.name}")

# Register Vaillant tools
mcp.tool()(vaillant_energy_consumption)
mcp.tool()(vaillant_advanced_diagnostics)
mcp.tool()(vaillant_get_topology)
mcp.tool()(vaillant_get_settings)
mcp.tool()(vaillant_get_state)
logger.info("Vaillant tools registered")

# Register Carbon Intensity tools
mcp.tool()(current_uk_grid_carbon_intensity_in_postcode)
mcp.tool()(carbon_intensity_history_and_forecast_for_postcode)
mcp.tool()(carbon_intensity_history_and_forecast_national)
mcp.tool()(current_national_generation_mix)
logger.info("Carbon Intensity tools registered")


def run(transport: Literal["stdio", "sse"] = "stdio") -> None:
    """Run the MCP server with the specified transport."""
    logger.info(f"Starting MCP server with transport: {transport}")
    mcp.run(transport)


if __name__ == "__main__":
    # Run the server with the specified transport
    logger.info(f"Command line arguments: {sys.argv}")
    if "sse" in sys.argv:
        run("sse")
    else:
        # Default to SSE transport if not specified
        run("stdio")
