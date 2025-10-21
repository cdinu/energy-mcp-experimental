import re
from datetime import datetime
from typing import Optional


def validate_and_parse_date(date_str: str) -> datetime | None:
    """Validate the datetime format YYYY-MM-DD or anything that can be parsed by datetime.

    Args:
        date_str: The date string to validate and parse

    Returns:
        A datetime object if valid, None otherwise
    """
    if not date_str:
        return None
    if not isinstance(date_str, str):
        return None
    if len(date_str) < 8:
        return None

    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None


def validate_datetime(datetime_str: str) -> datetime | None:
    """Validate and parse an ISO datetime string.

    Args:
        datetime_str: The datetime string to validate and parse

    Returns:
        A datetime object if valid, None otherwise
    """
    if not datetime_str:
        return None
    if not isinstance(datetime_str, str):
        return None

    try:
        # Handle 'Z' UTC designator by replacing with +00:00
        return datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
    except Exception:
        return None


def validate_vaillant_serial(serial: str) -> bool:
    """Validate the Vaillant serial number.

    Args:
        serial: The serial number to validate

    Returns:
        True if valid, False otherwise
    """
    if not serial:
        return False
    if not isinstance(serial, str):
        return False
    if len(serial) < 24:
        return False
    if not serial.startswith("2"):
        return False
    return True


def validate_and_parse_postcode(postcode: str) -> Optional[str]:
    """Validate a UK postcode and extract the outward code.

    UK postcodes follow the format: 1-2 letters, followed by 1-2 digits (optional space)
    followed by 1 digit and 2 letters. This function extracts the outward code
    (the part before the space or the last 3 characters).

    This validator also accepts just the outward code on its own.

    Args:
        postcode: The UK postcode or outward code to validate and parse

    Returns:
        The outward code if valid, None otherwise

    Examples:
        >>> validate_and_parse_postcode("SW1A 1AA")
        'SW1A'
        >>> validate_and_parse_postcode("SW1A1AA")
        'SW1A'
        >>> validate_and_parse_postcode("M1 1AA")
        'M1'
        >>> validate_and_parse_postcode("M11AA")
        'M1'
        >>> validate_and_parse_postcode("SW1A")  # Outward code only
        'SW1A'
        >>> validate_and_parse_postcode("M1")    # Outward code only
        'M1'
        >>> validate_and_parse_postcode("123")
        None
    """
    if not postcode:
        return None
    if not isinstance(postcode, str):
        return None

    # Remove all spaces and convert to uppercase
    postcode = re.sub(r"\s+", "", postcode).upper()

    # First check if it's a full postcode
    # UK postcode regex (simplified version)
    # Captures the outward code in group 1
    full_pattern = r"^([A-Z]{1,2}\d{1,2}[A-Z]?)(\d[A-Z]{2})$"
    match = re.match(full_pattern, postcode)
    if match:
        return match.group(1)

    # If not a full postcode, check if it's just an outward code
    outward_pattern = r"^([A-Z]{1,2}\d{1,2}[A-Z]?)$"
    match = re.match(outward_pattern, postcode)
    if match:
        return match.group(1)

    return None
