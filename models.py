"""
Data models for Philips Hue MCP Server.

This module contains dataclasses and type definitions used throughout
the application for representing Hue bridge context and state.
"""

from dataclasses import dataclass
from typing import Dict
from qhue import Bridge


@dataclass
class HueContext:
    """
    Context object holding the Hue bridge connection and cached state.

    Attributes:
        bridge: The qhue Bridge connection instance
        light_info: Cached dictionary of all light information
    """
    bridge: Bridge
    light_info: Dict  # Cache of light information
