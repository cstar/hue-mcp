"""
Utility functions for Philips Hue MCP Server.

This module contains helper functions for color conversion, validation,
fuzzy name matching, and data formatting.
"""

from typing import Dict, List, Optional, Tuple
from qhue import Bridge
from mcp.server.fastmcp import Context

from constants import FUZZY_MATCH_THRESHOLD


# ============================================================================
# CONTEXT HELPERS
# ============================================================================

def get_bridge_ctx(ctx: Context) -> Tuple[Bridge, Dict]:
    """
    Extract Hue bridge and light info from MCP context.

    Args:
        ctx: MCP Context object

    Returns:
        Tuple of (Bridge instance, light_info dictionary)
    """
    hue_ctx = ctx.request_context.lifespan_context
    return hue_ctx.bridge, hue_ctx.light_info


# ============================================================================
# COLOR CONVERSION
# ============================================================================

def rgb_to_xy(r: int, g: int, b: int) -> List[float]:
    """
    Convert RGB values to XY color space used by Philips Hue.

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        List containing [x, y] coordinates in the CIE color space
    """
    # Normalize RGB values
    r, g, b = r/255.0, g/255.0, b/255.0

    # Apply gamma correction
    r = pow(r, 2.2) if r > 0.04045 else r/12.92
    g = pow(g, 2.2) if g > 0.04045 else g/12.92
    b = pow(b, 2.2) if b > 0.04045 else b/12.92

    # Convert to XYZ using the Wide RGB D65 conversion matrix
    X = r * 0.649926 + g * 0.103455 + b * 0.197109
    Y = r * 0.234327 + g * 0.743075 + b * 0.022598
    Z = r * 0.000000 + g * 0.053077 + b * 1.035763

    # Calculate xy values from XYZ
    sum_XYZ = X + Y + Z
    if sum_XYZ == 0:
        return [0, 0]

    x = X / sum_XYZ
    y = Y / sum_XYZ

    return [x, y]


# Color presets for lights (defined after rgb_to_xy is available)
COLOR_PRESETS = {
    # White temperature presets
    "warm": {"ct": 2500},  # Warm white (2500K)
    "cool": {"ct": 4500},  # Cool white (4500K)
    "daylight": {"ct": 6500},  # Daylight (6500K)

    # Activity presets (Philips recommended settings)
    "concentration": {"ct": 4600, "bri": 254},  # Bright cool light
    "relax": {"ct": 2700, "bri": 144},  # Warm dimmed light
    "reading": {"ct": 3200, "bri": 219},  # Moderate neutral light
    "energize": {"ct": 6000, "bri": 254},  # Bright blue light

    # Color presets
    "red": {"xy": rgb_to_xy(255, 0, 0)},
    "green": {"xy": rgb_to_xy(0, 255, 0)},
    "blue": {"xy": rgb_to_xy(0, 0, 255)},
    "purple": {"xy": rgb_to_xy(128, 0, 128)},
    "orange": {"xy": rgb_to_xy(255, 165, 0)},
}


# ============================================================================
# VALIDATION
# ============================================================================

def validate_light_id(light_id: int, light_info: Dict) -> bool:
    """
    Check if a light ID exists in the light info cache.

    Args:
        light_id: The light ID to validate
        light_info: Dictionary of light information

    Returns:
        True if valid, False otherwise
    """
    return str(light_id) in light_info


def validate_group_id(group_id: int, bridge: Bridge) -> bool:
    """
    Check if a group ID exists on the bridge.

    Args:
        group_id: The group ID to validate
        bridge: Bridge connection instance

    Returns:
        True if valid, False otherwise
    """
    groups = bridge.groups()
    return str(group_id) in groups


def validate_light_id_with_suggestions(light_id: int, light_info: Dict) -> str:
    """
    Validate light ID and provide helpful error message with suggestions.

    Args:
        light_id: The light ID to validate
        light_info: Dictionary of light information

    Returns:
        Empty string if valid, error message with suggestions if invalid
    """
    if validate_light_id(light_id, light_info):
        return ""

    # Provide helpful suggestions
    available_lights = [f"{lid} ({light['name']})" for lid, light in light_info.items()]
    error_msg = f"Error: Light with ID {light_id} not found.\n"
    error_msg += f"Available light IDs: {', '.join(available_lights[:5])}"
    if len(available_lights) > 5:
        error_msg += f"... and {len(available_lights) - 5} more"

    return error_msg


def validate_group_id_with_suggestions(group_id: int, bridge: Bridge) -> str:
    """
    Validate group ID and provide helpful error message with suggestions.

    Args:
        group_id: The group ID to validate
        bridge: Bridge connection instance

    Returns:
        Empty string if valid, error message with suggestions if invalid
    """
    groups = bridge.groups()
    if validate_group_id(group_id, bridge):
        return ""

    # Provide helpful suggestions
    available_groups = [f"{gid} ({group['name']})" for gid, group in groups.items()]
    error_msg = f"Error: Group with ID {group_id} not found.\n"
    error_msg += f"Available group IDs: {', '.join(available_groups[:5])}"
    if len(available_groups) > 5:
        error_msg += f"... and {len(available_groups) - 5} more"

    return error_msg


# ============================================================================
# FUZZY NAME MATCHING
# ============================================================================

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate the Levenshtein distance (edit distance) between two strings.

    Args:
        s1: First string
        s2: Second string

    Returns:
        The minimum number of single-character edits needed to change s1 into s2
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def find_similar_names(search_name: str, items: Dict, threshold: int = FUZZY_MATCH_THRESHOLD) -> List[tuple]:
    """
    Find items with names similar to the search term using Levenshtein distance.

    Performs fuzzy matching with three strategies:
    1. Exact match (distance 0)
    2. Substring match (distance 1)
    3. Edit distance match (distance <= threshold)

    Args:
        search_name: The name to search for
        items: Dictionary of items with 'name' field
        threshold: Maximum edit distance to consider a match

    Returns:
        List of (id, name, distance) tuples sorted by distance, then by name
    """
    search_lower = search_name.lower()
    matches = []

    for item_id, item in items.items():
        item_name = item.get('name', '')
        item_name_lower = item_name.lower()

        # Exact match
        if search_lower == item_name_lower:
            matches.append((item_id, item_name, 0))
        # Substring match
        elif search_lower in item_name_lower:
            matches.append((item_id, item_name, 1))
        else:
            # Calculate edit distance
            distance = levenshtein_distance(search_lower, item_name_lower)
            if distance <= threshold:
                matches.append((item_id, item_name, distance))

    # Sort by distance, then by name
    matches.sort(key=lambda x: (x[2], x[1]))
    return matches


def find_light_by_name_fuzzy(name: str, light_info: Dict) -> Optional[tuple]:
    """
    Find a light by name using fuzzy matching.

    Args:
        name: Partial or misspelled light name
        light_info: Dictionary of light information

    Returns:
        Tuple of (light_id, light_name) if found, None otherwise
    """
    matches = find_similar_names(name, light_info, threshold=FUZZY_MATCH_THRESHOLD)
    return (matches[0][0], matches[0][1]) if matches else None


def find_group_by_name_fuzzy(name: str, bridge: Bridge) -> Optional[tuple]:
    """
    Find a group by name using fuzzy matching.

    Args:
        name: Partial or misspelled group name
        bridge: Bridge connection instance

    Returns:
        Tuple of (group_id, group_name) if found, None otherwise
    """
    groups = bridge.groups()
    matches = find_similar_names(name, groups, threshold=FUZZY_MATCH_THRESHOLD)
    return (matches[0][0], matches[0][1]) if matches else None


# ============================================================================
# FORMATTING
# ============================================================================

def format_light_info(light_info: Dict) -> Dict:
    """
    Format light information for display, extracting the most useful fields.

    Args:
        light_info: Raw light information dictionary from bridge

    Returns:
        Formatted dictionary with simplified light information
    """
    result = {}
    for light_id, light in light_info.items():
        # Extract the most useful information
        result[light_id] = {
            "name": light["name"],
            "on": light["state"]["on"],
            "reachable": light["state"].get("reachable", True),
            "brightness": light["state"].get("bri"),
            "color_mode": light["state"].get("colormode"),
            "type": light["type"],
            "model": light.get("modelid"),
            "manufacturer": light.get("manufacturername"),
        }
    return result
