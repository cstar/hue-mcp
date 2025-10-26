"""
Philips Hue Controller MCP Server

This server provides a Model Context Protocol (MCP) interface to control
Philips Hue lights. It exposes resources for retrieving light information
and tools for controlling lights.

Requirements:
- qhue: Python library for Philips Hue API
- mcp: Model Context Protocol Python SDK

Setup:
1. Install dependencies: uv sync (or pip install qhue mcp)
2. Update the bridge_ip in the config section if auto-discovery doesn't work
3. Run the server: python hue_server.py
4. Press the link button on your Hue bridge when prompted during first run
"""

# ============================================================================
# IMPORTS
# ============================================================================

# Standard library
import json
import logging

# Third-party
from mcp.server.fastmcp import FastMCP, Context
from qhue import create_new_username
from typing import Dict, List, Optional

# Local modules
from constants import DEFAULT_TRANSITION_TIME, VALID_ROOM_CLASSES, SCENE_TEMPLATES
from models import HueContext
from bridge import hue_lifespan
from utils import (
    get_bridge_ctx,
    rgb_to_xy,
    COLOR_PRESETS,
    validate_light_id,
    validate_group_id,
    validate_light_id_with_suggestions,
    validate_group_id_with_suggestions,
    find_similar_names,
    find_light_by_name_fuzzy,
    find_group_by_name_fuzzy,
    format_light_info,
)

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hue-mcp")

# ============================================================================
# MCP SERVER INITIALIZATION
# ============================================================================

# Create MCP server with lifespan management
mcp = FastMCP(
    "Philips Hue Controller",
    lifespan=hue_lifespan,
    dependencies=["qhue"]
)

# --- Convert Resources to Tools ---

@mcp.tool()
def get_all_lights(ctx: Context) -> str:
    """
    Get information about all lights connected to the Hue bridge.
    
    Returns:
        JSON string containing information about all lights
    """
    bridge, light_info = get_bridge_ctx(ctx)
    
    # Format the light information for better readability
    formatted_info = format_light_info(light_info)
    
    return json.dumps(formatted_info, indent=2)

@mcp.tool()
def get_light(light_id: int, ctx: Context) -> str:
    """
    Get detailed information about a specific light.
    
    Args:
        light_id: The ID of the light
        
    Returns:
        JSON string containing detailed information about the light
    """
    bridge, light_info = get_bridge_ctx(ctx)
    
    try:
        # Convert light_id to string for dict lookup
        light_id_str = str(light_id)
        
        # Check if the light exists
        if light_id_str not in light_info:
            return f"Error: Light with ID {light_id} not found."
        
        return json.dumps(light_info[light_id_str], indent=2)
    except Exception as e:
        logger.error(f"Error getting light {light_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_all_groups(ctx: Context) -> str:
    """
    Get information about all light groups.

    Returns:
        JSON string containing information about all groups
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()

        # Format the groups for better readability
        formatted_groups = {}
        for group_id, group in groups.items():
            formatted_groups[group_id] = {
                "name": group["name"],
                "type": group["type"],
                "lights": group["lights"],
                "on": group["state"]["all_on"],
                "any_on": group["state"]["any_on"]
            }

        return json.dumps(formatted_groups, indent=2)
    except Exception as e:
        logger.error(f"Error getting groups: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_group(group_id: int, ctx: Context) -> str:
    """
    Get information about a specific light group.
    
    Args:
        group_id: The ID of the group
        
    Returns:
        JSON string containing information about the group
    """
    bridge, _ = get_bridge_ctx(ctx)
    
    try:
        groups = bridge.groups()
        
        # Convert group_id to string for dict lookup
        group_id_str = str(group_id)
        
        # Check if the group exists
        if group_id_str not in groups:
            return f"Error: Group with ID {group_id} not found."
        
        return json.dumps(groups[group_id_str], indent=2)
    except Exception as e:
        logger.error(f"Error getting group {group_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_all_scenes(ctx: Context) -> str:
    """
    Get information about all scenes.
    
    Returns:
        JSON string containing information about all scenes
    """
    bridge, _ = get_bridge_ctx(ctx)
    
    try:
        scenes = bridge.scenes()
        
        # Format the scenes for better readability
        formatted_scenes = {}
        for scene_id, scene in scenes.items():
            formatted_scenes[scene_id] = {
                "name": scene.get("name", "Unknown"),
                "type": scene.get("type", "Unknown"),
                "group": scene.get("group"),
                "lights": scene.get("lights", []),
                "owner": scene.get("owner")
            }
        
        return json.dumps(formatted_scenes, indent=2)
    except Exception as e:
        logger.error(f"Error getting scenes: {e}")
        return f"Error: {str(e)}"

# ============================================================================
# TOOLS - Light and Group Control
# ============================================================================

# --- Individual Light Control ---

@mcp.tool()
def turn_on_light(light_id: int, ctx: Context) -> str:
    """
    Turn on a specific light by ID.
    
    Args:
        light_id: The ID of the light to turn on
        
    Returns:
        Confirmation message
    """
    bridge, light_info = get_bridge_ctx(ctx)
    
    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."

        # Use state endpoint for qhue
        bridge.lights[str(light_id)].state(on=True)
        return f"Light {light_id} ({light_info[str(light_id)]['name']}) turned on."
    except Exception as e:
        logger.error(f"Error turning on light {light_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def turn_off_light(light_id: int, ctx: Context) -> str:
    """
    Turn off a specific light by ID.
    
    Args:
        light_id: The ID of the light to turn off
        
    Returns:
        Confirmation message
    """
    bridge, light_info = get_bridge_ctx(ctx)
    
    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."

        # Use state endpoint for qhue
        bridge.lights[str(light_id)].state(on=False)
        return f"Light {light_id} ({light_info[str(light_id)]['name']}) turned off."
    except Exception as e:
        logger.error(f"Error turning off light {light_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def control_light_by_name(name: str, on: bool, ctx: Context) -> str:
    """
    Turn a light on or off by name using fuzzy matching.

    Args:
        name: Full or partial light name (fuzzy matching supported)
        on: True to turn on, False to turn off

    Returns:
        Confirmation message or "Did you mean?" suggestions
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Find matching lights
        matches = find_similar_names(name, light_info, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No lights found matching '{name}'.\nUse get_all_lights() to see available lights."

        # If exact or close match, use it
        if len(matches) == 1 or matches[0][2] == 0:
            light_id, light_name, distance = matches[0]
            bridge.lights[str(light_id)].state(on=on)
            action = "on" if on else "off"
            return f"Light '{light_name}' (ID: {light_id}) turned {action}."

        # Multiple matches - ask user to clarify
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
        return f"Multiple lights match '{name}'. Did you mean: {', '.join(suggestions)}?\nPlease use a more specific name or use the light ID."

    except Exception as e:
        logger.error(f"Error controlling light by name '{name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def control_group_by_name(name: str, on: bool, ctx: Context) -> str:
    """
    Turn a group on or off by name using fuzzy matching.

    Args:
        name: Full or partial group name (fuzzy matching supported)
        on: True to turn on, False to turn off

    Returns:
        Confirmation message or "Did you mean?" suggestions
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()

        # Find matching groups
        matches = find_similar_names(name, groups, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No groups found matching '{name}'.\nUse get_all_groups() to see available groups."

        # If exact or close match, use it
        if len(matches) == 1 or matches[0][2] == 0:
            group_id, group_name, distance = matches[0]
            bridge.groups[str(group_id)].action(on=on)
            action = "on" if on else "off"
            return f"Group '{group_name}' (ID: {group_id}) turned {action}."

        # Multiple matches - ask user to clarify
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
        return f"Multiple groups match '{name}'. Did you mean: {', '.join(suggestions)}?\nPlease use a more specific name or use the group ID."

    except Exception as e:
        logger.error(f"Error controlling group by name '{name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_brightness(light_id: int, brightness: int, ctx: Context, transition_time: int = DEFAULT_TRANSITION_TIME) -> str:
    """
    Set the brightness of a light with optional smooth transition.

    Args:
        light_id: The ID of the light
        brightness: Brightness level (0-254)
        transition_time: Transition duration in deciseconds (1 = 0.1s, 10 = 1s). Default: 4 (0.4s)

    Returns:
        Confirmation message
    """
    if not 0 <= brightness <= 254:
        return "Error: Brightness must be between 0 and 254."

    if transition_time < 0:
        return "Error: Transition time must be non-negative."

    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."

        # Turn on the light if it's off
        if not light_info[str(light_id)]['state']['on']:
            bridge.lights[str(light_id)].state(on=True)

        bridge.lights[str(light_id)].state(bri=brightness, transitiontime=transition_time)

        # Calculate brightness percentage for user feedback
        percentage = round((brightness / 254) * 100)
        transition_seconds = transition_time / 10
        return f"Light {light_id} ({light_info[str(light_id)]['name']}) brightness set to {brightness} ({percentage}%) with {transition_seconds}s transition."
    except Exception as e:
        logger.error(f"Error setting brightness for light {light_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_color_rgb(light_id: int, red: int, green: int, blue: int, ctx: Context, transition_time: int = DEFAULT_TRANSITION_TIME) -> str:
    """
    Set light color using RGB values with optional smooth transition.

    Args:
        light_id: The ID of the light
        red: Red value (0-255)
        green: Green value (0-255)
        blue: Blue value (0-255)
        transition_time: Transition duration in deciseconds (1 = 0.1s, 10 = 1s). Default: 4 (0.4s)

    Returns:
        Confirmation message
    """
    if not all(0 <= c <= 255 for c in (red, green, blue)):
        return "Error: RGB values must be between 0 and 255."

    if transition_time < 0:
        return "Error: Transition time must be non-negative."

    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."

        # Check if light supports color
        if 'xy' not in light_info[str(light_id)]['state']:
            return f"Error: Light {light_id} ({light_info[str(light_id)]['name']}) does not support color."

        # Turn on the light if it's off
        if not light_info[str(light_id)]['state']['on']:
            bridge.lights[str(light_id)].state(on=True)

        xy = rgb_to_xy(red, green, blue)
        bridge.lights[str(light_id)].state(xy=xy, transitiontime=transition_time)
        transition_seconds = transition_time / 10
        return f"Light {light_id} ({light_info[str(light_id)]['name']}) color set to RGB({red}, {green}, {blue}) with {transition_seconds}s transition."
    except Exception as e:
        logger.error(f"Error setting RGB color for light {light_id}: {e}")
        return f"Error: {str(e)}"

# --- Group Control ---

@mcp.tool()
def turn_on_group(group_id: int, ctx: Context) -> str:
    """
    Turn on all lights in a specific group.
    
    Args:
        group_id: The ID of the group
        
    Returns:
        Confirmation message
    """
    bridge, _ = get_bridge_ctx(ctx)
    
    try:
        # Validate group ID
        if not validate_group_id(group_id, bridge):
            return f"Error: Group with ID {group_id} not found."
        
        # Get group info for name
        group_info = bridge.groups[str(group_id)]()
        group_name = group_info.get('name', f"Group {group_id}")
        
        bridge.groups[str(group_id)].action(on=True)
        return f"Group {group_id} ({group_name}) turned on."
    except Exception as e:
        logger.error(f"Error turning on group {group_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def turn_off_group(group_id: int, ctx: Context) -> str:
    """
    Turn off all lights in a specific group.
    
    Args:
        group_id: The ID of the group
        
    Returns:
        Confirmation message
    """
    bridge, _ = get_bridge_ctx(ctx)
    
    try:
        # Validate group ID
        if not validate_group_id(group_id, bridge):
            return f"Error: Group with ID {group_id} not found."
        
        # Get group info for name
        group_info = bridge.groups[str(group_id)]()
        group_name = group_info.get('name', f"Group {group_id}")
        
        bridge.groups[str(group_id)].action(on=False)
        return f"Group {group_id} ({group_name}) turned off."
    except Exception as e:
        logger.error(f"Error turning off group {group_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_group_brightness(group_id: int, brightness: int, ctx: Context, transition_time: int = DEFAULT_TRANSITION_TIME) -> str:
    """
    Set the brightness of all lights in a group with optional smooth transition.

    Args:
        group_id: The ID of the group
        brightness: Brightness level (0-254)
        transition_time: Transition duration in deciseconds (1 = 0.1s, 10 = 1s). Default: 4 (0.4s)

    Returns:
        Confirmation message
    """
    if not 0 <= brightness <= 254:
        return "Error: Brightness must be between 0 and 254."

    if transition_time < 0:
        return "Error: Transition time must be non-negative."

    bridge, _ = get_bridge_ctx(ctx)

    try:
        # Validate group ID
        if not validate_group_id(group_id, bridge):
            return f"Error: Group with ID {group_id} not found."

        # Get group info for name
        group_info = bridge.groups[str(group_id)]()
        group_name = group_info.get('name', f"Group {group_id}")

        # Turn on the group if it's off
        if not group_info['state']['any_on']:
            bridge.groups[str(group_id)].action(on=True)

        bridge.groups[str(group_id)].action(bri=brightness, transitiontime=transition_time)

        # Calculate brightness percentage for user feedback
        percentage = round((brightness / 254) * 100)
        transition_seconds = transition_time / 10
        return f"Group {group_id} ({group_name}) brightness set to {brightness} ({percentage}%) with {transition_seconds}s transition."
    except Exception as e:
        logger.error(f"Error setting brightness for group {group_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_group_color_rgb(group_id: int, red: int, green: int, blue: int, ctx: Context, transition_time: int = DEFAULT_TRANSITION_TIME) -> str:
    """
    Set color for all lights in a group using RGB values with optional smooth transition.

    Args:
        group_id: The ID of the group
        red: Red value (0-255)
        green: Green value (0-255)
        blue: Blue value (0-255)
        transition_time: Transition duration in deciseconds (1 = 0.1s, 10 = 1s). Default: 4 (0.4s)

    Returns:
        Confirmation message
    """
    if not all(0 <= c <= 255 for c in (red, green, blue)):
        return "Error: RGB values must be between 0 and 255."

    if transition_time < 0:
        return "Error: Transition time must be non-negative."

    bridge, _ = get_bridge_ctx(ctx)

    try:
        # Validate group ID
        if not validate_group_id(group_id, bridge):
            return f"Error: Group with ID {group_id} not found."

        # Get group info for name
        group_info = bridge.groups[str(group_id)]()
        group_name = group_info.get('name', f"Group {group_id}")

        # Turn on the group if it's off
        if not group_info['state']['any_on']:
            bridge.groups[str(group_id)].action(on=True)

        xy = rgb_to_xy(red, green, blue)
        bridge.groups[str(group_id)].action(xy=xy, transitiontime=transition_time)
        transition_seconds = transition_time / 10
        return f"Group {group_id} ({group_name}) color set to RGB({red}, {green}, {blue}) with {transition_seconds}s transition."
    except Exception as e:
        logger.error(f"Error setting color for group {group_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_scene(group_id: int, scene_id: str, ctx: Context) -> str:
    """
    Apply a scene to a group.
    
    Args:
        group_id: The ID of the group
        scene_id: The ID of the scene
        
    Returns:
        Confirmation message
    """
    bridge, _ = get_bridge_ctx(ctx)
    
    try:
        # Validate group ID
        if not validate_group_id(group_id, bridge):
            return f"Error: Group with ID {group_id} not found."
        
        # Verify the scene exists
        scenes = bridge.scenes()
        if scene_id not in scenes:
            return f"Error: Scene with ID {scene_id} not found."
        
        # Get names for better feedback
        group_name = bridge.groups[str(group_id)]().get('name', f"Group {group_id}")
        scene_name = scenes[scene_id].get('name', f"Scene {scene_id}")
        
        bridge.groups[str(group_id)].action(scene=scene_id)
        return f"Scene '{scene_name}' applied to group '{group_name}'."
    except Exception as e:
        logger.error(f"Error applying scene {scene_id} to group {group_id}: {e}")
        return f"Error: {str(e)}"

# ============================================================================
# UTILITY TOOLS - Search, Presets, and Management
# ============================================================================

@mcp.tool()
def find_light_by_name(name: str, ctx: Context) -> str:
    """
    Find lights by searching their names.
    
    Args:
        name: Partial or full name to search for
        
    Returns:
        JSON string containing matching lights
    """
    _, light_info = get_bridge_ctx(ctx)
    
    try:
        # Search for lights with matching names (case-insensitive)
        name_lower = name.lower()
        matches = {}
        
        for light_id, light in light_info.items():
            if name_lower in light['name'].lower():
                matches[light_id] = {
                    "id": light_id,
                    "name": light['name'],
                    "type": light['type'],
                    "on": light['state']['on']
                }
        
        if not matches:
            return f"No lights found with name containing '{name}'."
        
        return json.dumps(matches, indent=2)
    except Exception as e:
        logger.error(f"Error finding lights by name '{name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def create_group(
    name: str, 
    light_ids: List[int], 
    ctx: Context
) -> str:
    """
    Create a new group of lights.
    
    Args:
        name: Name for the new group
        light_ids: List of light IDs to include in the group
        
    Returns:
        Confirmation message with group ID
    """
    bridge, light_info = get_bridge_ctx(ctx)
    
    try:
        # Validate all light IDs
        invalid_lights = [lid for lid in light_ids if not validate_light_id(lid, light_info)]
        if invalid_lights:
            return f"Error: Invalid light IDs: {invalid_lights}"
        
        # Convert light IDs to strings (Hue API requirement)
        light_id_strings = [str(lid) for lid in light_ids]

        # Create the group (qhue POST operation)
        # In qhue, we use the http_method parameter or call the resource with data
        import requests
        result = requests.post(
            f"http://{bridge.ip}/api/{bridge.username}/groups",
            json={"name": name, "lights": light_id_strings, "type": "LightGroup"}
        )
        result_data = result.json()

        # Extract the group ID from the result
        if result_data and isinstance(result_data, list) and len(result_data) > 0:
            if 'success' in result_data[0]:
                # Extract the ID from the success response
                # Format is usually: {"success":{"id":"/groups/1"}}
                success_dict = result_data[0]['success']
                if 'id' in success_dict:
                    group_id = success_dict['id'].split('/')[-1]
                    return f"Group '{name}' created with ID {group_id}, containing {len(light_ids)} lights."

        return f"Error creating group: {result_data}"
    except Exception as e:
        logger.error(f"Error creating group '{name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def quick_scene(
    name: str,
    ctx: Context,
    rgb: Optional[List[int]] = None,
    temperature: Optional[int] = None,
    brightness: Optional[int] = None,
    group_id: int = 0  # Default to group 0 (usually "All lights")
) -> str:
    """
    Quickly set up a lighting scene for a group.
    
    Args:
        name: Name for the scene
        rgb: Optional RGB values [r, g, b]
        temperature: Optional color temperature (2000-6500K)
        brightness: Optional brightness (0-254)
        group_id: Group ID to apply settings to (default: 0, usually "All lights")
        
    Returns:
        Confirmation message
    """
    bridge, light_info = get_bridge_ctx(ctx)
    
    try:
        # Validate group ID
        if not validate_group_id(group_id, bridge):
            return f"Error: Group with ID {group_id} not found."
        
        # Get group info for name
        group_info = bridge.groups[str(group_id)]()
        group_name = group_info.get('name', f"Group {group_id}")
        
        # Turn on the group
        bridge.groups[str(group_id)].action(on=True)
        
        # Apply settings
        if brightness is not None:
            if not 0 <= brightness <= 254:
                return "Error: Brightness must be between 0 and 254."
            bridge.groups[str(group_id)].action(bri=brightness)
        
        if rgb is not None:
            if not all(0 <= c <= 255 for c in rgb) or len(rgb) != 3:
                return "Error: RGB values must be three values between 0 and 255."
            xy = rgb_to_xy(rgb[0], rgb[1], rgb[2])
            bridge.groups[str(group_id)].action(xy=xy)
        
        if temperature is not None:
            if not 2000 <= temperature <= 6500:
                return "Error: Temperature must be between 2000K and 6500K."
            # Convert temperature in K to mired
            mired = int(1000000 / temperature)
            bridge.groups[str(group_id)].action(ct=mired)
        
        # Return a summary of what was applied
        changes = []
        if brightness is not None:
            changes.append(f"brightness {brightness} ({round((brightness / 254) * 100)}%)")
        if rgb is not None:
            changes.append(f"color RGB({rgb[0]}, {rgb[1]}, {rgb[2]})")
        if temperature is not None:
            changes.append(f"temperature {temperature}K")
        
        return f"Scene '{name}' applied to group '{group_name}' with {', '.join(changes)}."
    except Exception as e:
        logger.error(f"Error applying quick scene '{name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def refresh_lights(ctx: Context) -> str:
    """
    Refresh the light information cache.
    
    This is useful if lights have been added or removed, or if their state 
    has changed outside this application.
    
    Returns:
        Information about the refreshed lights
    """
    bridge, _ = get_bridge_ctx(ctx)
    
    try:
        # Update the bridge's internal state
        bridge.config()
        
        # Update our cache
        light_info = bridge.lights()
        ctx.request_context.lifespan_context.light_info = light_info
        
        return f"Refreshed information for {len(light_info)} lights."
    except Exception as e:
        logger.error(f"Error refreshing lights: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_color_preset(
    light_id: int, 
    preset: str, 
    ctx: Context
) -> str:
    """
    Apply a color preset to a light.

    Args:
        light_id: The ID of the light
        preset: Color preset name (warm, cool, daylight, concentration,
                relax, reading, energize, red, green, blue, purple, orange)

    Returns:
        Confirmation message
    """
    if preset not in COLOR_PRESETS:
        return f"Error: Unknown preset. Available presets: {', '.join(COLOR_PRESETS.keys())}"

    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."

        # Check capability for color temperature
        if "ct" in COLOR_PRESETS[preset] and 'ct' not in light_info[str(light_id)]['state']:
            return f"Error: Light {light_id} does not support color temperature."

        # Check capability for xy color
        if "xy" in COLOR_PRESETS[preset] and 'xy' not in light_info[str(light_id)]['state']:
            return f"Error: Light {light_id} does not support color."

        # Turn on the light if it's off
        if not light_info[str(light_id)]['state']['on']:
            bridge.lights[str(light_id)].state(on=True)

        # Apply preset settings
        for key, value in COLOR_PRESETS[preset].items():
            bridge.lights[str(light_id)].state(**{key: value})
        
        return f"Applied '{preset}' preset to light {light_id} ({light_info[str(light_id)]['name']})."
    except Exception as e:
        logger.error(f"Error applying preset '{preset}' to light {light_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_group_color_preset(
    group_id: int, 
    preset: str, 
    ctx: Context
) -> str:
    """
    Apply a color preset to a group.

    Args:
        group_id: The ID of the group
        preset: Color preset name (warm, cool, daylight, concentration,
                relax, reading, energize, red, green, blue, purple, orange)

    Returns:
        Confirmation message
    """
    if preset not in COLOR_PRESETS:
        return f"Error: Unknown preset. Available presets: {', '.join(COLOR_PRESETS.keys())}"
    
    bridge, _ = get_bridge_ctx(ctx)
    
    try:
        # Validate group ID
        if not validate_group_id(group_id, bridge):
            return f"Error: Group with ID {group_id} not found."
        
        # Get group info for name
        group_info = bridge.groups[str(group_id)]()
        group_name = group_info.get('name', f"Group {group_id}")
        
        # Turn on the group if it's off
        if not group_info['state']['any_on']:
            bridge.groups[str(group_id)].action(on=True)
        
        # Apply preset settings
        for key, value in COLOR_PRESETS[preset].items():
            bridge.groups[str(group_id)].action(**{key: value})
        
        return f"Applied '{preset}' preset to group '{group_name}'."
    except Exception as e:
        logger.error(f"Error applying preset '{preset}' to group {group_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def alert_light(light_id: int, ctx: Context) -> str:
    """
    Make a light flash briefly to identify it.
    
    Args:
        light_id: The ID of the light to alert
        
    Returns:
        Confirmation message
    """
    bridge, light_info = get_bridge_ctx(ctx)
    
    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."
        
        # Use the alert feature of Hue lights
        bridge.lights[str(light_id)].state(alert='select')
        
        return f"Light {light_id} ({light_info[str(light_id)]['name']}) alerted with a brief flash."
    except Exception as e:
        logger.error(f"Error alerting light {light_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_light_effect(light_id: int, effect: str, ctx: Context) -> str:
    """
    Set a dynamic effect on a light.
    
    Args:
        light_id: The ID of the light
        effect: Effect type ('none' or 'colorloop')
        
    Returns:
        Confirmation message
    """
    # Validate effect type
    valid_effects = ['none', 'colorloop']
    if effect not in valid_effects:
        return f"Error: Effect must be one of: {', '.join(valid_effects)}"
    
    bridge, light_info = get_bridge_ctx(ctx)
    
    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."
        
        # Check if light supports color (needed for effects)
        if 'xy' not in light_info[str(light_id)]['state']:
            return f"Error: Light {light_id} ({light_info[str(light_id)]['name']}) does not support color effects."
        
        # Turn on the light if it's off
        if not light_info[str(light_id)]['state']['on']:
            bridge.lights[str(light_id)].state(on=True)

        bridge.lights[str(light_id)].state(effect=effect)
        
        effect_name = "color loop" if effect == "colorloop" else "no effect"
        return f"Set {effect_name} on light {light_id} ({light_info[str(light_id)]['name']})."
    except Exception as e:
        logger.error(f"Error setting effect {effect} on light {light_id}: {e}")
        return f"Error: {str(e)}"

# ============================================================================
# CAPABILITY DISCOVERY - Inspect Light Features
# ============================================================================

@mcp.tool()
def get_light_capabilities(light_id: int, ctx: Context) -> str:
    """
    Get detailed information about what a specific light supports.

    Args:
        light_id: The ID of the light

    Returns:
        JSON string containing the light's capabilities (color, temperature, effects, etc.)
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate light ID
        if not validate_light_id(light_id, light_info):
            return f"Error: Light with ID {light_id} not found."

        light = light_info[str(light_id)]
        state = light['state']

        capabilities = {
            "light_id": light_id,
            "name": light['name'],
            "type": light['type'],
            "model": light.get('modelid', 'Unknown'),
            "manufacturer": light.get('manufacturername', 'Unknown'),
            "software_version": light.get('swversion', 'Unknown'),
            "capabilities": {
                "on_off": True,  # All lights support on/off
                "brightness": 'bri' in state,
                "color_xy": 'xy' in state,
                "color_temperature": 'ct' in state,
                "hue_saturation": 'hue' in state and 'sat' in state,
                "effects": 'effect' in state,
                "alerts": 'alert' in state,
                "color_mode": state.get('colormode', 'N/A')
            },
            "state": {
                "on": state['on'],
                "reachable": state.get('reachable', True),
                "brightness": state.get('bri'),
                "color_mode": state.get('colormode')
            }
        }

        # Add current color info if available
        if 'xy' in state:
            capabilities['state']['xy'] = state['xy']
        if 'ct' in state:
            capabilities['state']['color_temperature_mired'] = state['ct']
            # Convert mired to Kelvin for easier understanding
            capabilities['state']['color_temperature_kelvin'] = int(1000000 / state['ct'])
        if 'hue' in state:
            capabilities['state']['hue'] = state['hue']
        if 'sat' in state:
            capabilities['state']['saturation'] = state['sat']

        return json.dumps(capabilities, indent=2)

    except Exception as e:
        logger.error(f"Error getting capabilities for light {light_id}: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_all_capabilities(ctx: Context) -> str:
    """
    Get a summary of all lights and their capabilities.

    Returns:
        JSON string containing a summary of what each light can do
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        summary = {
            "total_lights": len(light_info),
            "lights": {}
        }

        # Count capability types
        capability_counts = {
            "color_xy": 0,
            "color_temperature": 0,
            "hue_saturation": 0,
            "effects": 0,
            "dimmable_only": 0
        }

        for light_id, light in light_info.items():
            state = light['state']

            # Determine light type
            light_type = "unknown"
            if 'xy' in state or ('hue' in state and 'sat' in state):
                light_type = "color"
                capability_counts["color_xy"] += 1
            elif 'ct' in state:
                light_type = "temperature"
                capability_counts["color_temperature"] += 1
            elif 'bri' in state:
                light_type = "dimmable"
                capability_counts["dimmable_only"] += 1

            if 'effect' in state:
                capability_counts["effects"] += 1

            summary["lights"][light_id] = {
                "name": light['name'],
                "type": light['type'],
                "model": light.get('modelid', 'Unknown'),
                "light_type": light_type,
                "capabilities": {
                    "brightness": 'bri' in state,
                    "color": 'xy' in state or ('hue' in state and 'sat' in state),
                    "temperature": 'ct' in state,
                    "effects": 'effect' in state
                },
                "reachable": state.get('reachable', True)
            }

        summary["capability_summary"] = {
            "color_lights": capability_counts["color_xy"],
            "temperature_lights": capability_counts["color_temperature"],
            "dimmable_only": capability_counts["dimmable_only"],
            "supports_effects": capability_counts["effects"]
        }

        return json.dumps(summary, indent=2)

    except Exception as e:
        logger.error(f"Error getting all capabilities: {e}")
        return f"Error: {str(e)}"

# ============================================================================
# SETUP AND DIAGNOSTICS - Connection and Health Tools
# ============================================================================

@mcp.tool()
def test_connection(ctx: Context) -> str:
    """
    Test the connection to the Hue bridge and verify authentication.

    Returns:
        Detailed connection status and any issues found
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Test basic connectivity
        config = bridge.config()

        # Test light access
        lights_count = len(light_info)

        # Test groups access
        groups = bridge.groups()
        groups_count = len(groups)

        # Test scenes access
        scenes = bridge.scenes()
        scenes_count = len(scenes)

        status = {
            "connection": "✓ Connected successfully",
            "authentication": "✓ Authenticated",
            "bridge_id": config.get('bridgeid', 'Unknown'),
            "api_version": config.get('apiversion', 'Unknown'),
            "software_version": config.get('swversion', 'Unknown'),
            "resources": {
                "lights": f"✓ {lights_count} lights accessible",
                "groups": f"✓ {groups_count} groups accessible",
                "scenes": f"✓ {scenes_count} scenes accessible"
            },
            "network": {
                "ip_address": config.get('ipaddress', 'Unknown'),
                "mac_address": config.get('mac', 'Unknown'),
                "netmask": config.get('netmask', 'Unknown'),
                "gateway": config.get('gateway', 'Unknown')
            }
        }

        return json.dumps(status, indent=2)

    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        error_info = {
            "connection": "✗ Connection failed",
            "error": str(e),
            "troubleshooting": [
                "1. Verify bridge IP address is correct",
                "2. Ensure bridge is powered on and connected to network",
                "3. Check if you need to re-authenticate (press link button)",
                "4. Verify network connectivity between server and bridge"
            ]
        }
        return json.dumps(error_info, indent=2)

@mcp.tool()
def get_bridge_info(ctx: Context) -> str:
    """
    Get detailed information about the Hue bridge.

    Returns:
        JSON string with comprehensive bridge information
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        config = bridge.config()

        bridge_info = {
            "identity": {
                "name": config.get('name', 'Unknown'),
                "bridge_id": config.get('bridgeid', 'Unknown'),
                "model_id": config.get('modelid', 'Unknown'),
                "manufacturer": "Signify (Philips Hue)"
            },
            "software": {
                "api_version": config.get('apiversion', 'Unknown'),
                "software_version": config.get('swversion', 'Unknown'),
                "software_update_available": config.get('swupdate', {}).get('updatestate', 0) == 2
            },
            "network": {
                "ip_address": config.get('ipaddress', 'Unknown'),
                "mac_address": config.get('mac', 'Unknown'),
                "netmask": config.get('netmask', 'Unknown'),
                "gateway": config.get('gateway', 'Unknown'),
                "dhcp": config.get('dhcp', False)
            },
            "features": {
                "portal_services": config.get('portalservices', False),
                "link_button": config.get('linkbutton', False),
                "touchlink": config.get('touchlink', False)
            },
            "timezone": config.get('timezone', 'Unknown'),
            "local_time": config.get('localtime', 'Unknown'),
            "utc_time": config.get('UTC', 'Unknown')
        }

        return json.dumps(bridge_info, indent=2)

    except Exception as e:
        logger.error(f"Error getting bridge info: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_connection_diagnostics(ctx: Context) -> str:
    """
    Run comprehensive diagnostics on the bridge connection.

    Returns:
        Detailed diagnostic report with recommendations
    """
    bridge, light_info = get_bridge_ctx(ctx)

    diagnostics = {
        "timestamp": json.dumps(bridge.config().get('UTC', 'Unknown')),
        "tests": []
    }

    # Test 1: Bridge connectivity
    try:
        config = bridge.config()
        diagnostics["tests"].append({
            "test": "Bridge Connectivity",
            "status": "✓ PASS",
            "details": f"Connected to bridge {config.get('name', 'Unknown')}"
        })
    except Exception as e:
        diagnostics["tests"].append({
            "test": "Bridge Connectivity",
            "status": "✗ FAIL",
            "details": str(e)
        })
        return json.dumps(diagnostics, indent=2)

    # Test 2: Authentication
    try:
        lights = bridge.lights()
        diagnostics["tests"].append({
            "test": "Authentication",
            "status": "✓ PASS",
            "details": "Successfully authenticated with bridge"
        })
    except Exception as e:
        diagnostics["tests"].append({
            "test": "Authentication",
            "status": "✗ FAIL",
            "details": "Authentication failed - may need to re-authenticate"
        })

    # Test 3: Light reachability
    unreachable = [f"{lid} ({light['name']})" for lid, light in light_info.items()
                   if not light['state'].get('reachable', True)]

    if unreachable:
        diagnostics["tests"].append({
            "test": "Light Reachability",
            "status": "⚠ WARNING",
            "details": f"{len(unreachable)} lights unreachable: {', '.join(unreachable[:3])}"
        })
    else:
        diagnostics["tests"].append({
            "test": "Light Reachability",
            "status": "✓ PASS",
            "details": f"All {len(light_info)} lights are reachable"
        })

    # Test 4: API version compatibility
    api_version = config.get('apiversion', '0.0.0')
    major_version = int(api_version.split('.')[0]) if api_version else 0

    if major_version >= 1:
        diagnostics["tests"].append({
            "test": "API Version",
            "status": "✓ PASS",
            "details": f"API version {api_version} is compatible"
        })
    else:
        diagnostics["tests"].append({
            "test": "API Version",
            "status": "⚠ WARNING",
            "details": f"API version {api_version} may have limited features"
        })

    # Summary and recommendations
    failed = sum(1 for t in diagnostics["tests"] if "✗" in t["status"])
    warnings = sum(1 for t in diagnostics["tests"] if "⚠" in t["status"])

    if failed == 0 and warnings == 0:
        diagnostics["summary"] = "All tests passed. System is functioning optimally."
    elif failed > 0:
        diagnostics["summary"] = f"{failed} test(s) failed. Immediate attention required."
        diagnostics["recommendations"] = [
            "Check bridge power and network connectivity",
            "Verify authentication credentials",
            "Consider re-running setup with test_connection()"
        ]
    else:
        diagnostics["summary"] = f"{warnings} warning(s) detected. System functional but may need attention."
        diagnostics["recommendations"] = [
            "Check unreachable lights - they may be powered off or out of range",
            "Consider updating bridge firmware if available"
        ]

    return json.dumps(diagnostics, indent=2)

# ============================================================================
# ROOM MANAGEMENT - Room Discovery, Control, and CRUD Operations
# ============================================================================

@mcp.tool()
def get_all_rooms(ctx: Context) -> str:
    """
    Get all rooms (groups with type='Room') created in the Hue app.

    Returns:
        JSON string containing information about all rooms
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()

        # Filter for rooms only (type='Room')
        rooms = {}
        for group_id, group in groups.items():
            if group.get('type') == 'Room':
                rooms[group_id] = {
                    "id": group_id,
                    "name": group['name'],
                    "room_class": group.get('class', 'Other'),
                    "lights": group['lights'],
                    "light_count": len(group['lights']),
                    "state": {
                        "all_on": group['state']['all_on'],
                        "any_on": group['state']['any_on']
                    }
                }

                # Add light names for convenience
                rooms[group_id]["light_names"] = [
                    light_info[lid]['name'] for lid in group['lights']
                    if lid in light_info
                ]

        if not rooms:
            return "No rooms found. Rooms can be created in the Hue app or using create_room()."

        return json.dumps({"total_rooms": len(rooms), "rooms": rooms}, indent=2)

    except Exception as e:
        logger.error(f"Error getting rooms: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_room(room_identifier: str, ctx: Context) -> str:
    """
    Get information about a specific room by ID or name.

    Args:
        room_identifier: Room ID (numeric string) or room name (fuzzy matching supported)

    Returns:
        JSON string containing detailed room information
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()

        # Try as ID first
        if room_identifier in groups and groups[room_identifier].get('type') == 'Room':
            group = groups[room_identifier]
            room_info = {
                "id": room_identifier,
                "name": group['name'],
                "room_class": group.get('class', 'Other'),
                "lights": group['lights'],
                "light_count": len(group['lights']),
                "state": group['state']
            }

            # Add detailed light info
            room_info["light_details"] = [
                {
                    "id": lid,
                    "name": light_info[lid]['name'],
                    "on": light_info[lid]['state']['on'],
                    "reachable": light_info[lid]['state'].get('reachable', True)
                }
                for lid in group['lights'] if lid in light_info
            ]

            return json.dumps(room_info, indent=2)

        # Try as name with fuzzy matching
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}
        matches = find_similar_names(room_identifier, rooms, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No room found matching '{room_identifier}'.\nUse get_all_rooms() to see available rooms."

        if len(matches) == 1 or matches[0][2] == 0:
            # Single or exact match
            room_id, room_name, distance = matches[0]
            group = groups[room_id]

            room_info = {
                "id": room_id,
                "name": group['name'],
                "room_class": group.get('class', 'Other'),
                "lights": group['lights'],
                "light_count": len(group['lights']),
                "state": group['state']
            }

            room_info["light_details"] = [
                {
                    "id": lid,
                    "name": light_info[lid]['name'],
                    "on": light_info[lid]['state']['on'],
                    "reachable": light_info[lid]['state'].get('reachable', True)
                }
                for lid in group['lights'] if lid in light_info
            ]

            return json.dumps(room_info, indent=2)

        # Multiple matches - ask for clarification
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
        return f"Multiple rooms match '{room_identifier}'. Did you mean: {', '.join(suggestions)}?\nPlease be more specific."

    except Exception as e:
        logger.error(f"Error getting room '{room_identifier}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def get_all_zones(ctx: Context) -> str:
    """
    Get all zones (groups with type='Zone') for multi-room groupings.

    Returns:
        JSON string containing information about all zones
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()

        # Filter for zones only (type='Zone')
        zones = {}
        for group_id, group in groups.items():
            if group.get('type') == 'Zone':
                zones[group_id] = {
                    "id": group_id,
                    "name": group['name'],
                    "zone_class": group.get('class', 'Other'),
                    "lights": group['lights'],
                    "light_count": len(group['lights']),
                    "state": {
                        "all_on": group['state']['all_on'],
                        "any_on": group['state']['any_on']
                    }
                }

                # Add light names
                zones[group_id]["light_names"] = [
                    light_info[lid]['name'] for lid in group['lights']
                    if lid in light_info
                ]

        if not zones:
            return "No zones found. Zones can be created using create_zone()."

        return json.dumps({"total_zones": len(zones), "zones": zones}, indent=2)

    except Exception as e:
        logger.error(f"Error getting zones: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def control_room(room_name: str, on: bool, ctx: Context) -> str:
    """
    Turn a room on or off by name using fuzzy matching.

    Args:
        room_name: Full or partial room name (fuzzy matching supported)
        on: True to turn on, False to turn off

    Returns:
        Confirmation message or "Did you mean?" suggestions
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        if not rooms:
            return "No rooms found. Rooms can be created in the Hue app or using create_room()."

        # Find matching rooms
        matches = find_similar_names(room_name, rooms, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No room found matching '{room_name}'.\nUse get_all_rooms() to see available rooms."

        # If exact or close match, use it
        if len(matches) == 1 or matches[0][2] == 0:
            room_id, room_name_matched, distance = matches[0]
            bridge.groups[str(room_id)].action(on=on)
            action = "on" if on else "off"
            room_class = rooms[room_id].get('class', 'Room')
            return f"{room_class} '{room_name_matched}' (ID: {room_id}) turned {action}."

        # Multiple matches - ask user to clarify
        suggestions = [f"'{m[1]}' (ID: {m[0]}, {rooms[m[0]].get('class', 'Room')})" for m in matches[:3]]
        return f"Multiple rooms match '{room_name}'. Did you mean: {', '.join(suggestions)}?\nPlease use a more specific name or use the room ID."

    except Exception as e:
        logger.error(f"Error controlling room '{room_name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_room_brightness(room_name: str, brightness: int, ctx: Context, transition_time: int = DEFAULT_TRANSITION_TIME) -> str:
    """
    Set the brightness of all lights in a room by name.

    Args:
        room_name: Full or partial room name (fuzzy matching supported)
        brightness: Brightness level (0-254)
        transition_time: Transition duration in deciseconds (1 = 0.1s, 10 = 1s). Default: 4 (0.4s)

    Returns:
        Confirmation message
    """
    if not 0 <= brightness <= 254:
        return "Error: Brightness must be between 0 and 254."

    if transition_time < 0:
        return "Error: Transition time must be non-negative."

    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        if not rooms:
            return "No rooms found. Rooms can be created in the Hue app or using create_room()."

        # Find matching rooms
        matches = find_similar_names(room_name, rooms, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No room found matching '{room_name}'.\nUse get_all_rooms() to see available rooms."

        if len(matches) == 1 or matches[0][2] == 0:
            room_id, room_name_matched, distance = matches[0]
            room = rooms[room_id]

            # Turn on if off
            if not room['state']['any_on']:
                bridge.groups[str(room_id)].action(on=True)

            bridge.groups[str(room_id)].action(bri=brightness, transitiontime=transition_time)

            percentage = round((brightness / 254) * 100)
            transition_seconds = transition_time / 10
            room_class = room.get('class', 'Room')
            return f"{room_class} '{room_name_matched}' brightness set to {brightness} ({percentage}%) with {transition_seconds}s transition."

        # Multiple matches
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
        return f"Multiple rooms match '{room_name}'. Did you mean: {', '.join(suggestions)}?"

    except Exception as e:
        logger.error(f"Error setting room brightness '{room_name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_room_color(room_name: str, red: int, green: int, blue: int, ctx: Context, transition_time: int = DEFAULT_TRANSITION_TIME) -> str:
    """
    Set the color of all lights in a room by name.

    Args:
        room_name: Full or partial room name (fuzzy matching supported)
        red: Red value (0-255)
        green: Green value (0-255)
        blue: Blue value (0-255)
        transition_time: Transition duration in deciseconds (1 = 0.1s, 10 = 1s). Default: 4 (0.4s)

    Returns:
        Confirmation message
    """
    if not all(0 <= c <= 255 for c in (red, green, blue)):
        return "Error: RGB values must be between 0 and 255."

    if transition_time < 0:
        return "Error: Transition time must be non-negative."

    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        if not rooms:
            return "No rooms found. Rooms can be created in the Hue app or using create_room()."

        # Find matching rooms
        matches = find_similar_names(room_name, rooms, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No room found matching '{room_name}'.\nUse get_all_rooms() to see available rooms."

        if len(matches) == 1 or matches[0][2] == 0:
            room_id, room_name_matched, distance = matches[0]
            room = rooms[room_id]

            # Turn on if off
            if not room['state']['any_on']:
                bridge.groups[str(room_id)].action(on=True)

            xy = rgb_to_xy(red, green, blue)
            bridge.groups[str(room_id)].action(xy=xy, transitiontime=transition_time)

            transition_seconds = transition_time / 10
            room_class = room.get('class', 'Room')
            return f"{room_class} '{room_name_matched}' color set to RGB({red}, {green}, {blue}) with {transition_seconds}s transition."

        # Multiple matches
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
        return f"Multiple rooms match '{room_name}'. Did you mean: {', '.join(suggestions)}?"

    except Exception as e:
        logger.error(f"Error setting room color '{room_name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def set_room_preset(room_name: str, preset: str, ctx: Context) -> str:
    """
    Apply a color preset to a room by name.

    Args:
        room_name: Full or partial room name (fuzzy matching supported)
        preset: Color preset name (warm, cool, daylight, concentration, relax, reading, energize, etc.)

    Returns:
        Confirmation message
    """
    if preset not in COLOR_PRESETS:
        return f"Error: Unknown preset. Available presets: {', '.join(COLOR_PRESETS.keys())}"

    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        if not rooms:
            return "No rooms found. Rooms can be created in the Hue app or using create_room()."

        # Find matching rooms
        matches = find_similar_names(room_name, rooms, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No room found matching '{room_name}'.\nUse get_all_rooms() to see available rooms."

        if len(matches) == 1 or matches[0][2] == 0:
            room_id, room_name_matched, distance = matches[0]
            room = rooms[room_id]

            # Turn on if off
            if not room['state']['any_on']:
                bridge.groups[str(room_id)].action(on=True)

            # Apply preset
            for key, value in COLOR_PRESETS[preset].items():
                bridge.groups[str(room_id)].action(**{key: value})

            room_class = room.get('class', 'Room')
            return f"Applied '{preset}' preset to {room_class} '{room_name_matched}'."

        # Multiple matches
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
        return f"Multiple rooms match '{room_name}'. Did you mean: {', '.join(suggestions)}?"

    except Exception as e:
        logger.error(f"Error setting room preset '{room_name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def create_room(
    name: str,
    light_ids: List[int],
    room_class: str = "Other",
    ctx: Context = None
) -> str:
    """
    Create a new room with specified lights.

    Args:
        name: Name for the new room
        light_ids: List of light IDs to include in the room
        room_class: Room type - Options: 'Living room', 'Kitchen', 'Dining', 'Bedroom',
                    'Kids bedroom', 'Bathroom', 'Nursery', 'Recreation', 'Office',
                    'Gym', 'Hallway', 'Toilet', 'Front door', 'Garage', 'Terrace',
                    'Garden', 'Driveway', 'Carport', 'Home', 'Downstairs', 'Upstairs',
                    'Top floor', 'Attic', 'Guest room', 'Staircase', 'Lounge', 'Man cave',
                    'Computer', 'Studio', 'Music', 'TV', 'Reading', 'Closet',
                    'Storage', 'Laundry room', 'Balcony', 'Porch', 'Barbecue', 'Pool', 'Other'

    Returns:
        Confirmation message with room ID
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate all light IDs
        invalid_lights = [lid for lid in light_ids if not validate_light_id(lid, light_info)]
        if invalid_lights:
            return f"Error: Invalid light IDs: {invalid_lights}"

        if not light_ids:
            return "Error: Room must contain at least one light."

        # Convert light IDs to strings
        light_id_strings = [str(lid) for lid in light_ids]

        # Create the room using direct API call
        import requests
        result = requests.post(
            f"http://{bridge.ip}/api/{bridge.username}/groups",
            json={
                "name": name,
                "lights": light_id_strings,
                "type": "Room",
                "class": room_class
            }
        )
        result_data = result.json()

        # Extract the room ID from the result
        if result_data and isinstance(result_data, list) and len(result_data) > 0:
            if 'success' in result_data[0]:
                success_dict = result_data[0]['success']
                if 'id' in success_dict:
                    room_id = success_dict['id'].split('/')[-1]
                    light_names = [light_info[str(lid)]['name'] for lid in light_ids]
                    return f"Room '{name}' (class: {room_class}) created with ID {room_id}.\nContains {len(light_ids)} lights: {', '.join(light_names)}"

        return f"Error creating room: {result_data}"

    except Exception as e:
        logger.error(f"Error creating room '{name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def add_lights_to_room(room_identifier: str, light_ids: List[int], ctx: Context) -> str:
    """
    Add lights to an existing room.

    Args:
        room_identifier: Room ID or name (fuzzy matching supported)
        light_ids: List of light IDs to add to the room

    Returns:
        Confirmation message
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate light IDs
        invalid_lights = [lid for lid in light_ids if not validate_light_id(lid, light_info)]
        if invalid_lights:
            return f"Error: Invalid light IDs: {invalid_lights}"

        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        # Find the room
        room_id = None
        room_name = None

        # Try as ID first
        if room_identifier in rooms:
            room_id = room_identifier
            room_name = rooms[room_id]['name']
        else:
            # Try name matching
            matches = find_similar_names(room_identifier, rooms, threshold=FUZZY_MATCH_THRESHOLD)
            if not matches:
                return f"Error: No room found matching '{room_identifier}'."
            if len(matches) > 1 and matches[0][2] != 0:
                suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
                return f"Multiple rooms match. Did you mean: {', '.join(suggestions)}?"
            room_id, room_name, _ = matches[0]

        # Get current lights in room
        current_lights = set(rooms[room_id]['lights'])

        # Add new lights
        new_lights = current_lights.union(str(lid) for lid in light_ids)

        # Update room
        import requests
        result = requests.put(
            f"http://{bridge.ip}/api/{bridge.username}/groups/{room_id}",
            json={"lights": list(new_lights)}
        )
        result_data = result.json()

        if result_data and isinstance(result_data, list) and 'success' in result_data[0]:
            added_names = [light_info[str(lid)]['name'] for lid in light_ids]
            return f"Added {len(light_ids)} lights to room '{room_name}': {', '.join(added_names)}"

        return f"Error updating room: {result_data}"

    except Exception as e:
        logger.error(f"Error adding lights to room '{room_identifier}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def remove_lights_from_room(room_identifier: str, light_ids: List[int], ctx: Context) -> str:
    """
    Remove lights from an existing room.

    Args:
        room_identifier: Room ID or name (fuzzy matching supported)
        light_ids: List of light IDs to remove from the room

    Returns:
        Confirmation message
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        # Find the room
        room_id = None
        room_name = None

        if room_identifier in rooms:
            room_id = room_identifier
            room_name = rooms[room_id]['name']
        else:
            matches = find_similar_names(room_identifier, rooms, threshold=FUZZY_MATCH_THRESHOLD)
            if not matches:
                return f"Error: No room found matching '{room_identifier}'."
            if len(matches) > 1 and matches[0][2] != 0:
                suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
                return f"Multiple rooms match. Did you mean: {', '.join(suggestions)}?"
            room_id, room_name, _ = matches[0]

        # Get current lights
        current_lights = set(rooms[room_id]['lights'])

        # Remove specified lights
        lights_to_remove = set(str(lid) for lid in light_ids)
        new_lights = current_lights - lights_to_remove

        if len(new_lights) == 0:
            return f"Error: Cannot remove all lights from room. Room must contain at least one light. Consider deleting the room instead."

        # Update room
        import requests
        result = requests.put(
            f"http://{bridge.ip}/api/{bridge.username}/groups/{room_id}",
            json={"lights": list(new_lights)}
        )
        result_data = result.json()

        if result_data and isinstance(result_data, list) and 'success' in result_data[0]:
            removed_names = [light_info[str(lid)]['name'] for lid in light_ids if str(lid) in lights_to_remove]
            return f"Removed {len(removed_names)} lights from room '{room_name}': {', '.join(removed_names)}"

        return f"Error updating room: {result_data}"

    except Exception as e:
        logger.error(f"Error removing lights from room '{room_identifier}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def delete_room(room_identifier: str, ctx: Context) -> str:
    """
    Delete a room.

    Args:
        room_identifier: Room ID or name (fuzzy matching supported)

    Returns:
        Confirmation message
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        # Find the room
        room_id = None
        room_name = None

        if room_identifier in rooms:
            room_id = room_identifier
            room_name = rooms[room_id]['name']
        else:
            matches = find_similar_names(room_identifier, rooms, threshold=FUZZY_MATCH_THRESHOLD)
            if not matches:
                return f"Error: No room found matching '{room_identifier}'."
            if len(matches) > 1 and matches[0][2] != 0:
                suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
                return f"Multiple rooms match. Did you mean: {', '.join(suggestions)}?"
            room_id, room_name, _ = matches[0]

        # Delete the room
        import requests
        result = requests.delete(
            f"http://{bridge.ip}/api/{bridge.username}/groups/{room_id}"
        )
        result_data = result.json()

        if result_data and isinstance(result_data, list) and 'success' in result_data[0]:
            return f"Room '{room_name}' (ID: {room_id}) deleted successfully. Note: The lights remain available and can be added to other rooms."

        return f"Error deleting room: {result_data}"

    except Exception as e:
        logger.error(f"Error deleting room '{room_identifier}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def create_zone(name: str, light_ids: List[int], ctx: Context, zone_class: str = "Other") -> str:
    """
    Create a new zone (multi-room grouping) with specified lights.

    Args:
        name: Name for the new zone
        light_ids: List of light IDs to include in the zone
        zone_class: Zone class (similar to room_class options)

    Returns:
        Confirmation message with zone ID
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate all light IDs
        invalid_lights = [lid for lid in light_ids if not validate_light_id(lid, light_info)]
        if invalid_lights:
            return f"Error: Invalid light IDs: {invalid_lights}"

        if not light_ids:
            return "Error: Zone must contain at least one light."

        # Convert light IDs to strings
        light_id_strings = [str(lid) for lid in light_ids]

        # Create the zone
        import requests
        result = requests.post(
            f"http://{bridge.ip}/api/{bridge.username}/groups",
            json={
                "name": name,
                "lights": light_id_strings,
                "type": "Zone",
                "class": zone_class
            }
        )
        result_data = result.json()

        if result_data and isinstance(result_data, list) and len(result_data) > 0:
            if 'success' in result_data[0]:
                success_dict = result_data[0]['success']
                if 'id' in success_dict:
                    zone_id = success_dict['id'].split('/')[-1]
                    light_names = [light_info[str(lid)]['name'] for lid in light_ids]
                    return f"Zone '{name}' created with ID {zone_id}.\nContains {len(light_ids)} lights: {', '.join(light_names)}"

        return f"Error creating zone: {result_data}"

    except Exception as e:
        logger.error(f"Error creating zone '{name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def control_zone(zone_name: str, on: bool, ctx: Context) -> str:
    """
    Turn a zone on or off by name using fuzzy matching.

    Args:
        zone_name: Full or partial zone name (fuzzy matching supported)
        on: True to turn on, False to turn off

    Returns:
        Confirmation message or suggestions
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        groups = bridge.groups()
        zones = {gid: g for gid, g in groups.items() if g.get('type') == 'Zone'}

        if not zones:
            return "No zones found. Zones can be created using create_zone()."

        # Find matching zones
        matches = find_similar_names(zone_name, zones, threshold=FUZZY_MATCH_THRESHOLD)

        if not matches:
            return f"Error: No zone found matching '{zone_name}'.\nUse get_all_zones() to see available zones."

        if len(matches) == 1 or matches[0][2] == 0:
            zone_id, zone_name_matched, distance = matches[0]
            bridge.groups[str(zone_id)].action(on=on)
            action = "on" if on else "off"
            return f"Zone '{zone_name_matched}' (ID: {zone_id}) turned {action}."

        # Multiple matches
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:3]]
        return f"Multiple zones match '{zone_name}'. Did you mean: {', '.join(suggestions)}?"

    except Exception as e:
        logger.error(f"Error controlling zone '{zone_name}': {e}")
        return f"Error: {str(e)}"

# ============================================================================
# SCENE MANAGEMENT - Advanced Scene Control and Templates
# ============================================================================

@mcp.tool()
def get_scene(scene_identifier: str, ctx: Context) -> str:
    """
    Get detailed information about a specific scene by ID or name.

    Supports fuzzy matching for scene names (e.g., "movie" matches "Movie Time").

    Args:
        scene_identifier: Scene ID or partial/full scene name

    Returns:
        JSON string with scene details or error message
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        scenes = bridge.scenes()

        # Try direct ID lookup first
        if scene_identifier in scenes:
            scene = scenes[scene_identifier]
            result = {
                "id": scene_identifier,
                "name": scene.get("name", "Unknown"),
                "type": scene.get("type", "Unknown"),
                "group": scene.get("group"),
                "lights": scene.get("lights", []),
                "owner": scene.get("owner"),
                "recycle": scene.get("recycle", False),
                "locked": scene.get("locked", False),
                "last_updated": scene.get("lastupdated")
            }
            return json.dumps(result, indent=2)

        # Try fuzzy name matching
        matches = find_similar_names(scene_identifier, scenes)

        if not matches:
            return f"Error: No scene found matching '{scene_identifier}'.\nUse get_all_scenes() to see available scenes."

        if len(matches) == 1 or matches[0][2] == 0:
            # Single match or exact match
            scene_id, scene_name, distance = matches[0]
            scene = scenes[scene_id]
            result = {
                "id": scene_id,
                "name": scene_name,
                "type": scene.get("type", "Unknown"),
                "group": scene.get("group"),
                "lights": scene.get("lights", []),
                "owner": scene.get("owner"),
                "recycle": scene.get("recycle", False),
                "locked": scene.get("locked", False),
                "last_updated": scene.get("lastupdated")
            }
            return json.dumps(result, indent=2)

        # Multiple matches - provide suggestions
        suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:5]]
        return f"Multiple scenes match '{scene_identifier}'. Did you mean:\n" + "\n".join(suggestions)

    except Exception as e:
        logger.error(f"Error getting scene '{scene_identifier}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def create_scene_from_current(
    name: str,
    room_or_group_id: int,
    ctx: Context,
    recycle: bool = True
) -> str:
    """
    Create a new scene from the current state of lights in a room/group.

    Captures the current brightness, color, and on/off state of all lights
    in the specified room or group.

    Args:
        name: Name for the new scene
        room_or_group_id: Room or group ID to capture lights from
        recycle: If True, scene can be auto-deleted to free space (default: True)

    Returns:
        Confirmation message with scene ID
    """
    bridge, light_info = get_bridge_ctx(ctx)

    try:
        # Validate group/room ID
        if not validate_group_id(room_or_group_id, bridge):
            return f"Error: Group/Room with ID {room_or_group_id} not found."

        # Get group info
        group_info = bridge.groups[str(room_or_group_id)]()
        group_name = group_info.get('name', f"Group {room_or_group_id}")
        lights_in_group = group_info.get('lights', [])

        if not lights_in_group:
            return f"Error: Group '{group_name}' has no lights."

        # Capture current state of each light
        light_states = {}
        for light_id in lights_in_group:
            if light_id in light_info:
                state = light_info[light_id]['state']
                light_states[light_id] = {
                    "on": state.get("on", False),
                    "bri": state.get("bri"),
                    "xy": state.get("xy"),
                    "ct": state.get("ct"),
                }
                # Remove None values
                light_states[light_id] = {k: v for k, v in light_states[light_id].items() if v is not None}

        # Create the scene via API
        import requests
        result = requests.post(
            f"http://{bridge.ip}/api/{bridge.username}/scenes",
            json={
                "name": name,
                "lights": lights_in_group,
                "recycle": recycle,
                "type": "GroupScene",
                "group": str(room_or_group_id),
                "lightstates": light_states
            }
        )

        response = result.json()
        if result.status_code == 200 and response and len(response) > 0:
            scene_id = response[0].get('success', {}).get('id')
            return f"Scene '{name}' created successfully with ID: {scene_id}\nCaptured {len(light_states)} lights from '{group_name}'."
        else:
            error_msg = response[0].get('error', {}).get('description', 'Unknown error')
            return f"Error creating scene: {error_msg}"

    except Exception as e:
        logger.error(f"Error creating scene from current state: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def delete_scene(scene_identifier: str, ctx: Context) -> str:
    """
    Delete a scene by ID or name.

    Supports fuzzy matching for scene names.

    Args:
        scene_identifier: Scene ID or partial/full scene name

    Returns:
        Confirmation message
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        scenes = bridge.scenes()
        scene_id = None
        scene_name = None

        # Try direct ID lookup first
        if scene_identifier in scenes:
            scene_id = scene_identifier
            scene_name = scenes[scene_identifier].get('name', 'Unknown')
        else:
            # Try fuzzy name matching
            matches = find_similar_names(scene_identifier, scenes)

            if not matches:
                return f"Error: No scene found matching '{scene_identifier}'.\nUse get_all_scenes() to see available scenes."

            if len(matches) > 1 and matches[0][2] != 0:
                # Multiple non-exact matches
                suggestions = [f"'{m[1]}' (ID: {m[0]})" for m in matches[:5]]
                return f"Multiple scenes match '{scene_identifier}'. Please be more specific:\n" + "\n".join(suggestions)

            scene_id, scene_name, _ = matches[0]

        # Delete the scene
        import requests
        result = requests.delete(
            f"http://{bridge.ip}/api/{bridge.username}/scenes/{scene_id}"
        )

        response = result.json()
        if result.status_code == 200 and response and len(response) > 0:
            if 'success' in response[0]:
                return f"Scene '{scene_name}' (ID: {scene_id}) deleted successfully."

        error_msg = response[0].get('error', {}).get('description', 'Unknown error')
        return f"Error deleting scene: {error_msg}"

    except Exception as e:
        logger.error(f"Error deleting scene '{scene_identifier}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def apply_scene_by_name(scene_name: str, room_name: str, ctx: Context) -> str:
    """
    Apply a scene to a room using fuzzy name matching for both.

    Makes it easy to recall scenes naturally, e.g.:
    - "Apply movie to living room"
    - "Set bedroom to relax"

    Args:
        scene_name: Scene name (fuzzy matching supported)
        room_name: Room name (fuzzy matching supported)

    Returns:
        Confirmation message
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        # Find the scene
        scenes = bridge.scenes()
        scene_matches = find_similar_names(scene_name, scenes)

        if not scene_matches:
            return f"Error: No scene found matching '{scene_name}'.\nUse get_all_scenes() to see available scenes."

        if len(scene_matches) > 1 and scene_matches[0][2] != 0:
            suggestions = [f"'{m[1]}'" for m in scene_matches[:3]]
            return f"Multiple scenes match '{scene_name}'. Did you mean: {', '.join(suggestions)}?"

        scene_id, scene_name_matched, _ = scene_matches[0]

        # Find the room
        groups = bridge.groups()
        rooms = {gid: g for gid, g in groups.items() if g.get('type') == 'Room'}

        if not rooms:
            return "No rooms found. Rooms can be created in the Hue app or using create_room()."

        room_matches = find_similar_names(room_name, rooms)

        if not room_matches:
            return f"Error: No room found matching '{room_name}'.\nUse get_all_rooms() to see available rooms."

        if len(room_matches) > 1 and room_matches[0][2] != 0:
            suggestions = [f"'{m[1]}'" for m in room_matches[:3]]
            return f"Multiple rooms match '{room_name}'. Did you mean: {', '.join(suggestions)}?"

        room_id, room_name_matched, _ = room_matches[0]

        # Apply the scene
        bridge.groups[str(room_id)].action(scene=scene_id)
        room_class = rooms[room_id].get('class', 'Room')

        return f"Scene '{scene_name_matched}' applied to {room_class} '{room_name_matched}'."

    except Exception as e:
        logger.error(f"Error applying scene '{scene_name}' to room '{room_name}': {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def list_scene_templates(ctx: Context = None) -> str:
    """
    List all available scene templates.

    Templates are pre-defined scene configurations for common scenarios
    like Movie Time, Dinner, Party, etc.

    Returns:
        JSON string with template names and descriptions
    """
    templates_info = {}
    for template_name, template_data in SCENE_TEMPLATES.items():
        templates_info[template_name] = {
            "description": template_data["description"],
            "brightness_percent": round((template_data["lights_state"].get("bri", 254) / 254) * 100),
            "has_color": "xy" in template_data["lights_state"],
            "has_temperature": "ct" in template_data["lights_state"]
        }

    return json.dumps(templates_info, indent=2)

@mcp.tool()
def create_scene_from_template(
    template_name: str,
    scene_name: str,
    room_or_group_id: int,
    ctx: Context,
    recycle: bool = True
) -> str:
    """
    Create a new scene from a pre-defined template.

    Available templates: Movie Time, Dinner, Party, Relax, Concentrate,
    Reading, Nightlight, Energize, Romantic, Wake Up

    Use list_scene_templates() to see all available templates with descriptions.

    Args:
        template_name: Name of the template to use (case-insensitive, fuzzy matching)
        scene_name: Name for the new scene
        room_or_group_id: Room or group ID to apply the scene to
        recycle: If True, scene can be auto-deleted to free space (default: True)

    Returns:
        Confirmation message with scene ID
    """
    bridge, _ = get_bridge_ctx(ctx)

    try:
        # Find matching template (case-insensitive, fuzzy)
        template_dict = {name.lower(): (name, data) for name, data in SCENE_TEMPLATES.items()}
        template_lower = template_name.lower()

        # Try exact match first
        if template_lower in template_dict:
            actual_template_name, template_data = template_dict[template_lower]
        else:
            # Try fuzzy matching
            template_search_dict = {name: {"name": name} for name in SCENE_TEMPLATES.keys()}
            matches = find_similar_names(template_name, template_search_dict)

            if not matches:
                available = ", ".join(SCENE_TEMPLATES.keys())
                return f"Error: Template '{template_name}' not found.\nAvailable templates: {available}\nUse list_scene_templates() for descriptions."

            if len(matches) > 1 and matches[0][2] != 0:
                suggestions = [f"'{m[1]}'" for m in matches[:3]]
                return f"Multiple templates match '{template_name}'. Did you mean: {', '.join(suggestions)}?"

            actual_template_name = matches[0][1]
            template_data = SCENE_TEMPLATES[actual_template_name]

        # Validate group/room ID
        if not validate_group_id(room_or_group_id, bridge):
            return f"Error: Group/Room with ID {room_or_group_id} not found."

        # Get group info
        group_info = bridge.groups[str(room_or_group_id)]()
        group_name = group_info.get('name', f"Group {room_or_group_id}")
        lights_in_group = group_info.get('lights', [])

        if not lights_in_group:
            return f"Error: Group '{group_name}' has no lights."

        # Apply template state to all lights
        light_states = {}
        for light_id in lights_in_group:
            light_states[light_id] = template_data["lights_state"].copy()

        # Create the scene via API
        import requests
        result = requests.post(
            f"http://{bridge.ip}/api/{bridge.username}/scenes",
            json={
                "name": scene_name,
                "lights": lights_in_group,
                "recycle": recycle,
                "type": "GroupScene",
                "group": str(room_or_group_id),
                "lightstates": light_states
            }
        )

        response = result.json()
        if result.status_code == 200 and response and len(response) > 0:
            scene_id = response[0].get('success', {}).get('id')
            return f"Scene '{scene_name}' created from template '{actual_template_name}' with ID: {scene_id}\nApplied to {len(light_states)} lights in '{group_name}'.\n\nDescription: {template_data['description']}"
        else:
            error_msg = response[0].get('error', {}).get('description', 'Unknown error')
            return f"Error creating scene: {error_msg}"

    except Exception as e:
        logger.error(f"Error creating scene from template '{template_name}': {e}")
        return f"Error: {str(e)}"

# --- Prompts ---

@mcp.prompt()
def control_lights() -> str:
    """
    A prompt for controlling lights with natural language.
    """
    return """
You are connected to a Philips Hue lighting system. I want to control my lights using natural language.
Please help me interpret my requests and use the appropriate tools to control my lighting.

First, if needed, retrieve information about my lights using the resources: hue://lights and hue://groups.
Then, use the appropriate tools to control the lights based on my request.

For example:
- Turn on or off specific lights or groups
- Change brightness or color
- Apply presets for different activities
- Set scenes or effects

Please confirm each action you take and provide feedback on the results.
"""

@mcp.prompt()
def create_mood() -> str:
    """
    A prompt for setting up mood lighting.
    """
    return """
You are connected to my Philips Hue lighting system. I want to create mood lighting for a specific activity
or atmosphere. Please help me set up the perfect lighting environment.

First, gather information about my available lights and groups.
Then, suggest and implement a lighting setup based on my mood or activity request.

Consider:
- Appropriate brightness levels for the activity
- Color temperature or colors that match the mood
- Using preset scenes or creating custom settings
- Grouping lights appropriately

After implementing, summarize what you've done and ask if I'd like to make adjustments.
"""

@mcp.prompt()
def light_schedule() -> str:
    """
    A prompt for explaining how to set up lighting schedules.
    """
    return """
I'd like to understand how to set up scheduled lighting with my Philips Hue system. 
Please explain the options available for scheduling automatic lighting changes, 
including:

- Whether scheduling is handled through the Hue app rather than this interface
- The types of schedules I can create (time-based, sunrise/sunset, etc.)
- How to create routines or scenes that can be scheduled
- Any limitations I should be aware of

After explaining the scheduling capabilities, suggest some useful lighting schedules
for typical home use.
"""

# --- Main Function ---

if __name__ == "__main__":
    # When run directly (not via MCP), use stdio transport
    # This allows the server to work with both:
    # - MCP clients (Claude Desktop, mcp dev, etc.) via stdio
    # - Direct HTTP access via SSE (use --transport sse flag)
    mcp.run()