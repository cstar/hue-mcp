"""
Constants and configuration for Philips Hue MCP Server.

This module contains all constant values used throughout the application,
including configuration paths, default values, and valid room classes.
"""

import os

# ============================================================================
# CONFIGURATION
# ============================================================================

# Bridge IP - can be set to None for auto-discovery
BRIDGE_IP = "192.168.1.10"  # Your bridge IP (set to None for auto-discovery)

# Path to store bridge connection info
CONFIG_DIR = os.path.expanduser("~/.hue-mcp")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# ============================================================================
# OPERATION DEFAULTS
# ============================================================================

# Default transition time in deciseconds (0.4 seconds)
DEFAULT_TRANSITION_TIME = 4

# Maximum Levenshtein distance for fuzzy name matching
FUZZY_MATCH_THRESHOLD = 3

# ============================================================================
# ROOM CLASSES
# ============================================================================

# Valid room classes for Philips Hue rooms
VALID_ROOM_CLASSES = (
    "Living room", "Kitchen", "Dining", "Bedroom", "Kids bedroom", "Bathroom",
    "Nursery", "Recreation", "Office", "Gym", "Hallway", "Toilet", "Front door",
    "Garage", "Terrace", "Garden", "Driveway", "Carport", "Home", "Downstairs",
    "Upstairs", "Top floor", "Attic", "Guest room", "Staircase", "Lounge",
    "Man cave", "Computer", "Studio", "Music", "TV", "Reading", "Closet",
    "Storage", "Laundry room", "Balcony", "Porch", "Barbecue", "Pool", "Other"
)
