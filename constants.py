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

# ============================================================================
# SCENE TEMPLATES
# ============================================================================

# Pre-defined scene templates for common scenarios
# Each template defines light states that can be applied to create a scene
SCENE_TEMPLATES = {
    "Movie Time": {
        "description": "Dim warm lighting for watching movies",
        "lights_state": {
            "on": True,
            "bri": 50,  # ~20% brightness
            "ct": 2700  # Warm white
        }
    },
    "Dinner": {
        "description": "Comfortable dining atmosphere",
        "lights_state": {
            "on": True,
            "bri": 180,  # ~70% brightness
            "ct": 3000  # Neutral warm
        }
    },
    "Party": {
        "description": "Bright energetic lighting",
        "lights_state": {
            "on": True,
            "bri": 254,  # 100% brightness
            "xy": [0.3127, 0.329]  # Bright white
        }
    },
    "Relax": {
        "description": "Soft warm lighting for relaxation",
        "lights_state": {
            "on": True,
            "bri": 144,  # ~55% brightness
            "ct": 2200  # Very warm
        }
    },
    "Concentrate": {
        "description": "Bright cool lighting for focus",
        "lights_state": {
            "on": True,
            "bri": 254,  # 100% brightness
            "ct": 4600  # Cool white
        }
    },
    "Reading": {
        "description": "Moderate neutral lighting for reading",
        "lights_state": {
            "on": True,
            "bri": 219,  # ~85% brightness
            "ct": 3200  # Neutral
        }
    },
    "Nightlight": {
        "description": "Very dim warm lighting for nighttime",
        "lights_state": {
            "on": True,
            "bri": 20,  # ~8% brightness
            "ct": 2000  # Very warm
        }
    },
    "Energize": {
        "description": "Bright cool lighting for energy",
        "lights_state": {
            "on": True,
            "bri": 254,  # 100% brightness
            "ct": 6000  # Cool daylight
        }
    },
    "Romantic": {
        "description": "Soft colored lighting for romance",
        "lights_state": {
            "on": True,
            "bri": 100,  # ~40% brightness
            "xy": [0.5614, 0.4156]  # Soft red/pink
        }
    },
    "Wake Up": {
        "description": "Gradual bright warm lighting",
        "lights_state": {
            "on": True,
            "bri": 200,  # ~80% brightness
            "ct": 3500  # Neutral warm
        }
    }
}
