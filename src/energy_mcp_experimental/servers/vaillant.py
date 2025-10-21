import os
from datetime import datetime
from typing import Literal

from energy_mcp_experimental.tools.validators import validate_and_parse_date

try:
    from vaillant_client.api import VaillantApi, VaillantApiConfig
    _vaillant_import_error = None
except ImportError as exc:  # pragma: no cover - optional dependency
    VaillantApi = VaillantApiConfig = None  # type: ignore[assignment]
    _vaillant_import_error = exc


_VAILLANT_DEPENDENCY_MESSAGE = (
    "Vaillant tools require the experimental `vaillant-client` package. "
    "Install it from https://github.com/cdinu/vaillant-client and retry."
)


def vaillant_energy_consumption(
    from_datetime_yyyy_mm_dd: str,
    to_datetime_yyyy_mm_dd: str,
    scale: Literal["hourly", "daily", "monthly"],
) -> str:
    """Vaillant Heatpump Energy Consumption - from_datetime format is YYYY-MM-DD, to_datetime format YYYY-MM-DD, scale is one of hourly, daily, monthly

    Get the energy consumption of the Vaillant heat pump/boiler. This function retrieves energy data including
    electricity usage, environmental yield, and heat generated for central heating and domestic hot water.

    Args:
        from_datetime_yyyy_mm_dd: Start date in YYYY-MM-DD format
        to_datetime_yyyy_mm_dd: End date in YYYY-MM-DD format
        scale: Data granularity - hourly, daily, or monthly
    """
    if VaillantApi is None or _vaillant_import_error is not None:
        return _VAILLANT_DEPENDENCY_MESSAGE + (
            f" (import error: {_vaillant_import_error})"
            if _vaillant_import_error
            else ""
        )

    serial = os.getenv("VAILLANT_SERIAL", "UNKNOWN")

    if serial == "UNKNOWN":
        return "Vaillant heat pump serial number not found."

    from_datetime = validate_and_parse_date(from_datetime_yyyy_mm_dd)
    to_datetime = validate_and_parse_date(to_datetime_yyyy_mm_dd)
    if from_datetime is None or to_datetime is None:
        return "Invalid date format. Please use YYYY-MM-DD or a valid format."

    # use vaillant client to retrieve energy consumption
    config = VaillantApiConfig()
    api = VaillantApi(config, [serial])

    try:
        consumption = api.get_components_consumption(
            serial, scale, from_datetime, to_datetime
        )

        if consumption is None:
            return "No energy consumption data available."

        if not consumption:
            return f"No consumption data found for the period {from_datetime} to {to_datetime}."

        # Format the response to be LLM-friendly
        system = consumption[0]  # Take the first system if multiple are returned

        # Mask the serial number for privacy
        serial_short = "V" + system.systemComponentSerialNumber[24:]
        system.systemComponentSerialNumber = serial_short

        # Convert timestamps to datetime objects
        for c in system.consumptions:
            c.from_ = datetime.fromtimestamp(c.from_)
            c.to = datetime.fromtimestamp(c.to)

        # Convert total consumption from Wh to kWh with 1 decimal place
        total_consumption_kwh = round(system.totalConsumption / 1000, 1)

        result = "# Vaillant Heat Pump Energy Consumption\n\n"

        result += f"Device: {serial_short} ({system.deviceType})\n"
        result += f"Period: {from_datetime} to {to_datetime}\n"
        result += f"Data granularity: {scale}\n"
        result += f"Total consumption: {total_consumption_kwh} kWh\n\n"

        # Get consumption by time period in table format - better for parsing and graphing
        result += "## Detailed Consumption by Period\n\n"

        # Calculate totals
        total_electricity = 0
        total_env_yield = 0
        total_generated = 0

        # Define table headers
        result += "| Period | CH Elec (kWh) | CH Env (kWh) | CH Heat (kWh) | CH COP | DHW Elec (kWh) | DHW Env (kWh) | DHW Heat (kWh) | DHW COP | Total Elec (kWh) | Total Heat (kWh) | Overall COP |\n"
        result += "|--------|--------------|--------------|---------------|--------|----------------|---------------|----------------|---------|-----------------|-----------------|------------|\n"

        # Use all periods, up to 336 entries (enough for 2 weeks of hourly data)
        max_periods = min(336, len(system.consumptions))
        display_periods = system.consumptions[:max_periods]

        for period in display_periods:
            period_start = period.from_
            # period_end = period.to
            period_str = f"{period_start.strftime('%Y-%m-%d %H:%M')}"

            # Central Heating - convert from Wh to kWh with 1 decimal place
            ch_elec_wh = period.centralHeating.electricity or 0
            ch_env_wh = period.centralHeating.environmentalYield or 0
            ch_gen_wh = period.centralHeating.generated or 0

            ch_elec = round(ch_elec_wh / 1000, 1)
            ch_env = round(ch_env_wh / 1000, 1)
            ch_gen = round(ch_gen_wh / 1000, 1)
            ch_cop = round(ch_gen_wh / ch_elec_wh, 1) if ch_elec_wh > 0 else 0

            # Domestic Hot Water - convert from Wh to kWh with 1 decimal place
            dhw_elec_wh = 0
            dhw_env_wh = 0
            dhw_gen_wh = 0

            if period.domesticHotWater:
                dhw_elec_wh = period.domesticHotWater.electricity or 0
                dhw_env_wh = period.domesticHotWater.environmentalYield or 0
                dhw_gen_wh = period.domesticHotWater.generated or 0

            dhw_elec = round(dhw_elec_wh / 1000, 1)
            dhw_env = round(dhw_env_wh / 1000, 1)
            dhw_gen = round(dhw_gen_wh / 1000, 1)
            dhw_cop = round(dhw_gen_wh / dhw_elec_wh, 1) if dhw_elec_wh > 0 else 0

            # Totals for this period in Wh (for running totals)
            period_elec_wh = ch_elec_wh + dhw_elec_wh
            period_heat_wh = ch_gen_wh + dhw_gen_wh

            # Totals for this period in kWh (for display)
            period_elec = round(period_elec_wh / 1000, 1)
            period_heat = round(period_heat_wh / 1000, 1)
            period_cop = (
                round(period_heat_wh / period_elec_wh, 1) if period_elec_wh > 0 else 0
            )

            # Add to running totals (in Wh)
            total_electricity += period_elec_wh
            total_env_yield += ch_env_wh + dhw_env_wh
            total_generated += period_heat_wh

            # Add table row
            result += f"| {period_str} | {ch_elec} | {ch_env} | {ch_gen} | {ch_cop} | {dhw_elec} | {dhw_env} | {dhw_gen} | {dhw_cop} | {period_elec} | {period_heat} | {period_cop} |\n"

        # If there are more periods than we displayed
        if len(system.consumptions) > max_periods:
            result += f"\n*Note: Showing {max_periods} of {len(system.consumptions)} periods.*\n\n"

        # Summary - convert totals from Wh to kWh with 1 decimal place
        total_electricity_kwh = round(total_electricity / 1000, 1)
        total_env_yield_kwh = round(total_env_yield / 1000, 1)
        total_generated_kwh = round(total_generated / 1000, 1)

        result += "## Summary\n\n"
        result += f"Total electricity consumed: {total_electricity_kwh} kWh\n"
        result += f"Total environmental yield: {total_env_yield_kwh} kWh\n"
        result += f"Total heat generated: {total_generated_kwh} kWh\n"

        # Add explanation of the columns for LLM understanding
        result += "\n**Column Definitions:**\n"
        result += "- **CH**: Central Heating\n"
        result += "- **DHW**: Domestic Hot Water\n"
        result += "- **Elec**: Electricity Consumption kWh\n"
        result += "- **Env**: Environmental Yield  kWh\n"
        result += "- **Heat**: Heating Total kWh\n"

        result += "*Heat pumps extract energy from the environment (air/ground) and use electricity to convert it to usable heat. The Coefficient of Performance (COP) measures efficiency - a COP of 3.5 means 3.5 units of heat produced for every 1 unit of electricity used.*\n\n"

        if total_electricity > 0:
            overall_cop = round(total_generated / total_electricity, 1)
            result += f"Overall COP: {overall_cop}\n"

        return result

    except Exception as e:
        return f"Failed to fetch energy consumption: {e}"


def vaillant_advanced_diagnostics() -> str:
    """Vaillant Heatpump Advanced Diagnosis - Get the advanced diagnostics of the Vaillant heat pump, boiler, or control system.

    This function retrieves detailed diagnostic information from the Vaillant heat pump, including operational
    parameters such as temperatures, pressures, valve positions, pump status, and performance metrics.

    The data includes system status, temperatures, operational hours, efficiency metrics, and component states.
    """
    if VaillantApi is None or _vaillant_import_error is not None:
        return _VAILLANT_DEPENDENCY_MESSAGE + (
            f" (import error: {_vaillant_import_error})"
            if _vaillant_import_error
            else ""
        )

    serial = os.getenv("VAILLANT_SERIAL", "UNKNOWN")

    if serial == "UNKNOWN":
        return "Vaillant heat pump serial number not found."

    # use vaillant client to retrieve advanced diagnostics
    config = VaillantApiConfig()
    api = VaillantApi(config, [serial])

    try:
        diagnostics = api.get_advanced_diagnostics(serial, include_metadata=True)

        if diagnostics is None:
            return "No diagnostics data available."

        # Format the response to be LLM-friendly
        result = "# Vaillant Heat Pump Advanced Diagnostics\n\n"

        # Process each device/component in the diagnostic data
        for diag in diagnostics.root:
            # Mask the serial number for privacy
            if diag.serialNumber is not None:
                diag.serialNumber = "V" + diag.serialNumber[24:]
                result += f"## Device: {diag.serialNumber}\n"

            # System status
            result += "## System Status\n\n"

            # Add active/inactive status
            if hasattr(diag, "compressorActive"):
                result += f"- Compressor: {'Active' if diag.compressorActive else 'Inactive'}\n"
            if hasattr(diag, "heatingPumpActive"):
                result += f"- Heating pump: {'Active' if diag.heatingPumpActive else 'Inactive'}\n"
            if hasattr(diag, "blocked"):
                result += f"- System blocked: {'Yes' if diag.blocked else 'No'}\n"
            if hasattr(diag, "frostProtectionActive"):
                result += f"- Frost protection: {'Active' if diag.frostProtectionActive else 'Inactive'}\n"
            if hasattr(diag, "sanitaryOrLoadingPumpActive"):
                result += f"- Sanitary/loading pump: {'Active' if diag.sanitaryOrLoadingPumpActive else 'Inactive'}\n"
            if hasattr(diag, "solarPumpActive"):
                result += f"- Solar pump: {'Active' if diag.solarPumpActive else 'Inactive'}\n"

            # Temperature readings
            result += "\n## Temperature Readings\n\n"

            temp_fields = [
                ("outdoorTemperature", "Outdoor temperature"),
                ("flowTemperature", "Flow temperature"),
                ("returnTemperature", "Return temperature"),
                ("airInletTemperature", "Air inlet temperature"),
                ("evaporationTemperature", "Evaporation temperature"),
                ("condensationTemperature", "Condensation temperature"),
                ("heatExchangerInletTemperature", "Heat exchanger inlet temperature"),
                ("heatExchangerOutletTemperature", "Heat exchanger outlet temperature"),
                ("inletTemperature", "Inlet temperature"),
                ("outletTemperature", "Outlet temperature"),
                ("roomTemperature", "Room temperature"),
                ("roomTemperatureTarget", "Room temperature target"),
            ]

            for field, label in temp_fields:
                if hasattr(diag, field) and getattr(diag, field) is not None:
                    value = getattr(diag, field)
                    result += f"- {label}: {value}°C\n"

            # Performance metrics
            result += "\n## Performance Metrics\n\n"

            # Operational hours and counters
            if hasattr(diag, "operatingHours") and diag.operatingHours is not None:
                result += f"- Operating hours: {diag.operatingHours} hours\n"
            if hasattr(diag, "compressorStarts") and diag.compressorStarts is not None:
                result += f"- Compressor starts: {diag.compressorStarts}\n"
            if (
                hasattr(diag, "safetyRelayCommutations")
                and diag.safetyRelayCommutations is not None
            ):
                result += (
                    f"- Safety relay commutations: {diag.safetyRelayCommutations}\n"
                )
            if (
                hasattr(diag, "safetyRelayOperatingHours")
                and diag.safetyRelayOperatingHours is not None
            ):
                result += f"- Safety relay operating hours: {diag.safetyRelayOperatingHours} hours\n"

            # Component settings
            result += "\n## Component Settings\n\n"

            # Valves and component positions
            if (
                hasattr(diag, "electronicExpansionValvePosition")
                and diag.electronicExpansionValvePosition is not None
            ):
                result += f"- Electronic expansion valve position: {diag.electronicExpansionValvePosition}%\n"
            if hasattr(diag, "fanSpeed") and diag.fanSpeed is not None:
                fan_units = getattr(diag, "fanUnits", "rpm")
                result += f"- Fan speed: {diag.fanSpeed} {fan_units}\n"
            if hasattr(diag, "frequencySignal") and diag.frequencySignal is not None:
                result += f"- Frequency signal: {diag.frequencySignal} Hz\n"
            if hasattr(diag, "waterPressure") and diag.waterPressure is not None:
                result += f"- Water pressure: {diag.waterPressure} bar\n"
            if (
                hasattr(diag, "highPressureSensor")
                and diag.highPressureSensor is not None
            ):
                result += f"- High pressure sensor: {diag.highPressureSensor} bar\n"

            # Heating data
            if (
                hasattr(diag, "desiredFlowTemperature")
                and diag.desiredFlowTemperature is not None
            ):
                result += (
                    f"- Desired flow temperature: {diag.desiredFlowTemperature}°C\n"
                )
            if hasattr(diag, "heatingDemand") and diag.heatingDemand is not None:
                result += f"- Heating demand: {diag.heatingDemand}%\n"

            # Refrigerant circuit details
            result += "\n## Refrigerant Circuit\n\n"

            if (
                hasattr(diag, "currentSubcooling")
                and diag.currentSubcooling is not None
            ):
                result += f"- Current subcooling: {diag.currentSubcooling}K\n"
            if (
                hasattr(diag, "setpointSubcooling")
                and diag.setpointSubcooling is not None
            ):
                result += f"- Setpoint subcooling: {diag.setpointSubcooling}K\n"
            if (
                hasattr(diag, "currentSuperheating")
                and diag.currentSuperheating is not None
            ):
                result += f"- Current superheating: {diag.currentSuperheating}K\n"
            if (
                hasattr(diag, "targetSuperheating")
                and diag.targetSuperheating is not None
            ):
                result += f"- Target superheating: {diag.targetSuperheating}K\n"
            if (
                hasattr(diag, "condenserDeltaTemperature")
                and diag.condenserDeltaTemperature is not None
            ):
                result += f"- Condenser delta temperature: {diag.condenserDeltaTemperature}K\n"

        return result
    except Exception as e:
        return f"Failed to fetch diagnostics: {e}"


def vaillant_get_topology() -> str:
    """Vaillant System Topology - Get the system topology for the Vaillant heat pump/boiler

    This function retrieves the system topology, showing all devices connected to the system.
    The topology includes device serial numbers, types, and other identifying information.
    """
    if VaillantApi is None or _vaillant_import_error is not None:
        return _VAILLANT_DEPENDENCY_MESSAGE + (
            f" (import error: {_vaillant_import_error})"
            if _vaillant_import_error
            else ""
        )

    serial = os.getenv("VAILLANT_SERIAL", "UNKNOWN")

    if serial == "UNKNOWN":
        return "Vaillant heat pump serial number not found."

    # use vaillant client to retrieve topology
    config = VaillantApiConfig()
    api = VaillantApi(config, [serial])

    try:
        topology = api.get_topology(serial)

        if not topology:
            return "No topology data available."

        # Format the response to be LLM-friendly
        result = "# Vaillant System Topology\n\n"

        # Add basic information
        result += f"Last changed at: {topology.lastChangedAt}\n"
        result += f"Last data received at: {topology.lastDataReceivedAt}\n\n"

        # List devices
        result += f"## Devices ({len(topology.devices)})\n\n"

        if not topology.devices:
            result += "No devices found in the system.\n"
        else:
            # Create table for devices
            result += "| Serial Number | Type | Subtype | Marketing Name | Nomenclature | Article Number |\n"
            result += "|---------------|------|---------|----------------|--------------|----------------|\n"

            for device in topology.devices:
                # Mask the serial number for privacy (show only last few characters)
                masked_serial = (
                    "V" + device.serialNumber[24:]
                    if len(device.serialNumber) > 24
                    else device.serialNumber
                )

                # Handle optional fields
                subtype = device.subType or "N/A"
                marketing_name = device.marketingName or "N/A"
                nomenclature = device.nomenclature or "N/A"
                article_number = device.articleNumber or "N/A"

                result += f"| {masked_serial} | {device.type} | {subtype} | {marketing_name} | {nomenclature} | {article_number} |\n"

        # Handle unidentified devices if present
        if topology.unidentifiedDevices:
            result += (
                f"\n## Unidentified Devices ({len(topology.unidentifiedDevices)})\n\n"
            )

            result += "| Type | Subtype | Bus Coupler Address | eBUS Address |\n"
            result += "|------|---------|---------------------|-------------|\n"

            for device in topology.unidentifiedDevices:
                result += f"| {device.type} | {device.subType} | {device.location.busCouplerAddress} | {device.location.ebusAddress} |\n"

        return result

    except Exception as e:
        return f"Failed to fetch topology: {e}"


def vaillant_get_settings() -> str:
    """Vaillant System Settings - Get the current settings for the Vaillant heat pump/boiler

    This function retrieves the current system settings, including operation modes,
    temperature targets, and schedule information.
    """
    if VaillantApi is None or _vaillant_import_error is not None:
        return _VAILLANT_DEPENDENCY_MESSAGE + (
            f" (import error: {_vaillant_import_error})"
            if _vaillant_import_error
            else ""
        )

    serial = os.getenv("VAILLANT_SERIAL", "UNKNOWN")

    if serial == "UNKNOWN":
        return "Vaillant heat pump serial number not found."

    # use vaillant client to retrieve settings
    config = VaillantApiConfig()
    api = VaillantApi(config, [serial])

    try:
        settings_response = api.get_system_settings(serial, include_metadata=True)

        if not settings_response or not settings_response.root:
            return "No settings data available."

        # Format the response to be LLM-friendly
        result = "# Vaillant System Settings\n\n"

        # Process each device's settings
        for settings in settings_response.root:
            # Mask the serial number for privacy
            masked_serial = (
                "V" + settings.serialNumber[24:]
                if len(settings.serialNumber) > 24
                else settings.serialNumber
            )

            result += f"## Device: {masked_serial} ({settings.type})\n\n"

            # General settings
            result += "### General Settings\n\n"
            if settings.date:
                result += f"- Date: {settings.date}\n"
            if settings.time:
                result += f"- Time: {settings.time}\n"
            if settings.hoursTillService is not None:
                result += f"- Hours till service: {settings.hoursTillService}\n"
            if settings.mode:
                result += f"- Mode: {settings.mode}\n"
            if settings.activeSchedule:
                result += f"- Active schedule: {settings.activeSchedule}\n"

            # Central Heating settings
            if settings.centralHeating:
                ch = settings.centralHeating
                result += "\n### Central Heating\n\n"

                if ch.enabled is not None:
                    result += f"- Enabled: {ch.enabled}\n"
                if ch.roomTemperatureTarget is not None:
                    result += (
                        f"- Room temperature target: {ch.roomTemperatureTarget}°C\n"
                    )
                if ch.useSchedule is not None:
                    result += f"- Use schedule: {ch.useSchedule}\n"
                if ch.powerOutput is not None:
                    result += f"- Power output: {ch.powerOutput}\n"
                if ch.powerOutputMode:
                    result += f"- Power output mode: {ch.powerOutputMode}\n"

                # Manual override
                if ch.manualOverride:
                    result += "\n#### Manual Override\n\n"
                    result += f"- Enabled: {ch.manualOverride.enabled}\n"
                    if ch.manualOverride.until:
                        override_until = datetime.fromtimestamp(ch.manualOverride.until)
                        result += f"- Until: {override_until}\n"
                    if ch.manualOverride.roomTemperatureTarget:
                        result += f"- Room temperature target: {ch.manualOverride.roomTemperatureTarget}°C\n"

                # Away override
                if ch.awayOverride:
                    result += "\n#### Away Override\n\n"
                    result += f"- Enabled: {ch.awayOverride.enabled}\n"
                    if ch.awayOverride.until:
                        override_until = datetime.fromtimestamp(ch.awayOverride.until)
                        result += f"- Until: {override_until}\n"
                    if ch.awayOverride.roomTemperatureTarget:
                        result += f"- Room temperature target: {ch.awayOverride.roomTemperatureTarget}°C\n"

            # Domestic Hot Water settings
            if settings.domesticHotWater:
                dhw = settings.domesticHotWater
                result += "\n### Domestic Hot Water\n\n"

                if dhw.temperatureTarget is not None:
                    result += f"- Temperature target: {dhw.temperatureTarget}°C\n"

                # Boost
                if dhw.boost:
                    result += "\n#### Boost\n\n"
                    result += f"- Enabled: {dhw.boost.enabled}\n"
                    if dhw.boost.until:
                        boost_until = datetime.fromtimestamp(dhw.boost.until)
                        result += f"- Until: {boost_until}\n"

            # Temperature corrections
            if settings.temperatureCorrections:
                result += "\n### Temperature Corrections\n\n"
                for key, value in settings.temperatureCorrections.items():
                    result += f"- {key}: {value}\n"

            result += "\n---\n\n"  # Separator between devices

        return result

    except Exception as e:
        return f"Failed to fetch settings: {e}"


def vaillant_get_state() -> str:
    """Vaillant System State - Get the current state of the Vaillant heat pump/boiler

    This function retrieves the current system state, including operating parameters,
    temperatures, and component status information.
    """
    if VaillantApi is None or _vaillant_import_error is not None:
        return _VAILLANT_DEPENDENCY_MESSAGE + (
            f" (import error: {_vaillant_import_error})"
            if _vaillant_import_error
            else ""
        )

    serial = os.getenv("VAILLANT_SERIAL", "UNKNOWN")

    if serial == "UNKNOWN":
        return "Vaillant heat pump serial number not found."

    # use vaillant client to retrieve state
    config = VaillantApiConfig()
    api = VaillantApi(config, [serial])

    try:
        state_data = api.get_system_state(serial, include_metadata=True)

        if not state_data:
            return "No state data available."

        # Format the response to be LLM-friendly
        result = "# Vaillant System State\n\n"

        # Since the state data doesn't have a predefined schema in the client library,
        # we'll handle it as a generic dictionary and format it based on common fields

        # Check if it's a list or a single object
        if isinstance(state_data, list):
            for i, device_state in enumerate(state_data):
                result += format_device_state(device_state, i)
        else:
            result += format_device_state(state_data, 0)

        return result

    except Exception as e:
        return f"Failed to fetch system state: {e}"


def format_device_state(state_data: dict, index: int) -> str:
    """Helper function to format a device state into a readable string."""
    result = ""

    # Get device identity info
    serial = state_data.get("serialNumber", f"Device {index + 1}")
    device_type = state_data.get("type", "Unknown")

    # Mask the serial number for privacy
    if isinstance(serial, str) and len(serial) > 24:
        masked_serial = "V" + serial[24:]
    else:
        masked_serial = serial

    result += f"## Device: {masked_serial} ({device_type})\n\n"

    # Process common temperature fields
    temperatures = []
    for key in state_data:
        if (
            "temperature" in key.lower()
            and key != "serialNumber"
            and isinstance(state_data[key], (int, float))
        ):
            temperatures.append((key, state_data[key]))

    if temperatures:
        result += "### Temperatures\n\n"
        for name, value in temperatures:
            # Format key name to make it more readable
            readable_name = name.replace("Temperature", " Temperature")
            readable_name = "".join(
                " " + char if char.isupper() else char for char in readable_name
            ).strip()
            readable_name = readable_name.capitalize()

            result += f"- {readable_name}: {value}°C\n"
        result += "\n"

    # Process status fields (boolean values)
    statuses = []
    for key in state_data:
        if isinstance(state_data[key], bool) and key != "serialNumber":
            statuses.append((key, state_data[key]))

    if statuses:
        result += "### Status Indicators\n\n"
        for name, value in statuses:
            # Format key name to make it more readable
            readable_name = "".join(
                " " + char if char.isupper() else char for char in name
            ).strip()
            readable_name = readable_name.capitalize()

            status_text = "Active" if value else "Inactive"
            result += f"- {readable_name}: {status_text}\n"
        result += "\n"

    # Process nested objects
    for key, value in state_data.items():
        if isinstance(value, dict) and key != "_metadata":
            result += f"### {key.capitalize()}\n\n"
            for subkey, subvalue in value.items():
                if isinstance(subvalue, dict):
                    # Handle nested dictionaries (one level deep)
                    result += f"#### {subkey.capitalize()}\n\n"
                    for subsubkey, subsubvalue in subvalue.items():
                        readable_name = "".join(
                            " " + char if char.isupper() else char for char in subsubkey
                        ).strip()
                        readable_name = readable_name.capitalize()
                        result += f"- {readable_name}: {subsubvalue}\n"
                else:
                    # Handle regular key-value pairs
                    readable_name = "".join(
                        " " + char if char.isupper() else char for char in subkey
                    ).strip()
                    readable_name = readable_name.capitalize()

                    # Add units for known fields
                    if "temperature" in subkey.lower() and isinstance(
                        subvalue, (int, float)
                    ):
                        result += f"- {readable_name}: {subvalue}°C\n"
                    elif "pressure" in subkey.lower() and isinstance(
                        subvalue, (int, float)
                    ):
                        result += f"- {readable_name}: {subvalue} bar\n"
                    elif isinstance(subvalue, bool):
                        status_text = "Active" if subvalue else "Inactive"
                        result += f"- {readable_name}: {status_text}\n"
                    else:
                        result += f"- {readable_name}: {subvalue}\n"
            result += "\n"

    return result
