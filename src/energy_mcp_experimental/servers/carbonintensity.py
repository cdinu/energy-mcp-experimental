from datetime import datetime
from typing import Any, Dict, Literal, Optional

import requests
from energy_mcp_experimental.tools.validators import (
    validate_and_parse_postcode,
    validate_datetime,
)

BASE_URL = "https://api.carbonintensity.org.uk"


def _make_request(endpoint: str) -> Dict[str, Any]:
    """Make a request to the Carbon Intensity API."""
    response = requests.get(f"{BASE_URL}{endpoint}")
    response.raise_for_status()
    return dict(response.json())


def current_uk_grid_carbon_intensity_in_postcode(post_code: str | None = None) -> str:
    """Current UK Grid Carbon Intensity in Postcode - Get the current carbon intensity for your postcode.


    This function retrieves the current carbon intensity for the user's postcode from the Carbon Intensity API.
    The postcode if not provided, is read from the USER_POSTCODE environment variable.

    The response includes:
    - Region ID and details
    - Carbon intensity forecast value and index level
    - Generation mix with percentages by fuel type
    """
    full_postcode = post_code

    if not full_postcode:
        return "User postcode not found. Please provide a postcode or set the USER_POSTCODE environment variable on the MCP server"

    outward_code = validate_and_parse_postcode(full_postcode)
    if not outward_code:
        return f"Invalid UK postcode format: {full_postcode}. Please provide a valid UK postcode."

    try:
        endpoint = f"/regional/postcode/{outward_code}"
        data = _make_request(endpoint)

        if not data or "data" not in data or not data["data"]:
            return f"No carbon intensity data available for postcode {outward_code}."

        # Format the response to be LLM-friendly
        result = f"Carbon intensity for {full_postcode} (outward code: {outward_code}, {data['data'][0]['shortname']}):\n\n"

        intensity_data = data["data"][0]["data"][0]
        intensity = intensity_data["intensity"]

        result += f"Time period: {intensity_data['from']} to {intensity_data['to']}\n"
        result += f"Carbon intensity: {intensity['forecast']} gCO2/kWh ({intensity['index']} level)\n\n"

        # Add generation mix information
        result += "Generation mix:\n"
        for fuel in intensity_data["generationmix"]:
            if fuel["perc"] > 0:
                result += f"- {fuel['fuel'].capitalize()}: {fuel['perc']}%\n"

        return result

    except Exception as e:
        return f"Failed to fetch carbon intensity data: {e}"


def carbon_intensity_history_and_forecast_for_postcode(
    from_datetime: str | None = None,
    forecast_hours: Literal["24", "48"] = "24",
    postcode: Optional[str] = None,
) -> str:
    """UK Grid Carbon Intensity History and Forecast for Postcode - from_datetime format is ISO 8601 (e.g., 2025-05-01T01:00Z), forecast_hours is 24 or 48

    This function retrieves the carbon intensity forecast for either 24 or 48 hours after the specified datetime.
    If a postcode is provided, it will return data specific to that location; otherwise, it returns national data.

    The response includes the carbon intensity forecast values and index levels for each time period.
    """

    from_dt: datetime | None = None

    if from_datetime is None:
        from_dt = datetime.now()
    else:
        from_dt = validate_datetime(from_datetime)

    if from_dt is None:
        return "Invalid datetime format. Please use ISO 8601 format (e.g., 2025-05-01T01:00Z)."

    outward_code = None
    if postcode:
        outward_code = validate_and_parse_postcode(postcode)
        if not outward_code:
            return f"Invalid UK postcode format: {postcode}. Please provide a valid UK postcode."

    try:
        if outward_code:
            endpoint = f"/regional/intensity/{from_dt.isoformat()}/fw{forecast_hours}h/postcode/{outward_code}"
        else:
            endpoint = f"/intensity/{from_dt.isoformat()}/fw{forecast_hours}h"

        data = _make_request(endpoint)

        if not data:
            return "No forecast data available for the specified parameters."

        # Format the response to be LLM-friendly
        if outward_code:
            location = data["data"]["shortname"]
            result = f"Carbon intensity forecast for {postcode} (outward code: {outward_code}, {location}) for {forecast_hours} hours from {from_dt.isoformat()}:\n\n"
            forecast_data = data["data"]["data"]
        else:
            result = f"**National** carbon intensity forecast for {forecast_hours} hours from {from_dt.isoformat()} in gCO2/kWh and its intensity:\n\n"
            forecast_data = data["data"]

        for i, period in enumerate(forecast_data):
            intensity = period["intensity"]
            result += f"{i + 1}. {period['from']} to {period['to']}: {intensity.get('forecast', 'N/A')}  {intensity.get('index', 'N/A')}\n"

        return result

    except Exception as e:
        return f"Failed to fetch carbon intensity forecast: {e}"


def carbon_intensity_history_and_forecast_national(
    from_datetime: str | None = None,
    forecast_hours: Literal["24", "48"] = "24",
    format_type: Literal["list", "table"] = "table",
) -> str:
    """UK National Grid Carbon Intensity History and Forecast - from_datetime format is ISO 8601 (e.g., 2025-05-01T01:00Z), forecast_hours is 24 or 48

    This function retrieves the national carbon intensity forecast for either 24 or 48 hours after the specified datetime.

    Args:
        from_datetime: Starting datetime in ISO 8601 format (e.g., 2025-05-01T01:00Z). If None, current time is used.
        forecast_hours: Number of hours to forecast - either "24" or "48"
        format_type: Output format - "list" or "table" (default: "table")

    Returns:
        Formatted string with forecast data
    """
    from_dt: datetime | None = None

    if from_datetime is None:
        from_dt = datetime.now()
    else:
        from_dt = validate_datetime(from_datetime)

    if from_dt is None:
        return "Invalid datetime format. Please use ISO 8601 format (e.g., 2025-05-01T01:00Z)."

    try:
        # Get national carbon intensity forecast
        endpoint = f"/intensity/{from_dt.isoformat()}/fw{forecast_hours}h"
        data = _make_request(endpoint)

        if not data or "data" not in data:
            return "No forecast data available for the specified parameters."

        forecast_data = data["data"]

        # Format the response based on the requested format
        if format_type == "list":
            result = "# UK National Carbon Intensity Forecast\n\n"
            result += f"Starting from: {from_dt.isoformat()}\n"
            result += f"Forecast duration: {forecast_hours} hours\n\n"

            # List format (similar to previous implementation)
            for i, period in enumerate(forecast_data):
                intensity = period["intensity"]
                result += f"{i + 1}. {period['from']} to {period['to']}: {intensity.get('forecast', 'N/A')} gCO2/kWh ({intensity.get('index', 'N/A')} level)\n"

        else:  # Table format (better for analysis and parsing)
            result = "# UK National Carbon Intensity Forecast\n\n"
            result += f"Starting from: {from_dt.isoformat()}\n"
            result += f"Forecast duration: {forecast_hours} hours\n\n"

            # Add brief explanation for LLM understanding
            result += "*Carbon intensity measures how much CO2 is emitted per unit of electricity generated (gCO2/kWh).*\n"
            result += "*Lower values are better for the environment. Index ranges: very low, low, moderate, high, very high.*\n\n"

            # Table format
            result += "| # | From | To | Forecast (gCO2/kWh) | Intensity Level |\n"
            result += "|---|------|----|--------------------|----------------|\n"

            for i, period in enumerate(forecast_data):
                intensity = period["intensity"]
                forecast_value = intensity.get("forecast", "N/A")
                intensity_level = intensity.get("index", "N/A")

                # Add row to table
                result += f"| {i + 1} | {period['from']} | {period['to']} | {forecast_value} | {intensity_level} |\n"

        return result

    except Exception as e:
        return f"Failed to fetch carbon intensity forecast: {e}"


def current_national_generation_mix() -> str:
    """Current UK National Generation Mix - Get the current national electricity generation mix.

    This function retrieves the current national electricity generation mix from the Carbon Intensity API.

    The response includes percentages of electricity generated by different fuel types.
    """
    try:
        endpoint = "/generation"
        data = _make_request(endpoint)

        if not data or "data" not in data or not data["data"]:
            return "No generation mix data available."

        mix_data = data["data"]["generationmix"]
        from_time = data["data"]["from"]
        to_time = data["data"]["to"]

        # Format the response to be LLM-friendly
        result = f"UK National Generation Mix ({from_time} to {to_time}):\n\n"

        # Sort by percentage (descending)
        mix_data.sort(key=lambda x: x["perc"], reverse=True)

        for fuel in mix_data:
            if fuel["perc"] > 0:
                result += f"- {fuel['fuel'].capitalize()}: {fuel['perc']}%\n"

        return result

    except Exception as e:
        return f"Failed to fetch generation mix data: {e}"
