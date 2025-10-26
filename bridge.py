"""
Bridge connection and lifecycle management for Philips Hue MCP Server.

This module handles discovering, connecting to, and maintaining the connection
with the Philips Hue bridge, including authentication and configuration management.
"""

import os
import json
import logging
import requests
from typing import Optional
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from qhue import Bridge, QhueException
from mcp.server.fastmcp import FastMCP

from constants import BRIDGE_IP, CONFIG_DIR, CONFIG_FILE
from models import HueContext


# Configure logging
logger = logging.getLogger("hue-mcp")


# ============================================================================
# BRIDGE DISCOVERY
# ============================================================================

def discover_bridge() -> Optional[str]:
    """
    Attempt to discover Hue bridge on the local network using Philips API.

    Returns:
        Bridge IP address if found, None otherwise
    """
    try:
        logger.info("Attempting bridge discovery via Hue discovery API...")
        response = requests.get("https://discovery.meethue.com/", timeout=5)
        if response.status_code == 200:
            bridges = response.json()
            if bridges and len(bridges) > 0:
                bridge_ip = bridges[0].get('internalipaddress')
                logger.info(f"Discovered bridge at {bridge_ip}")
                return bridge_ip
    except Exception as e:
        logger.warning(f"Bridge discovery failed: {e}")
    return None


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def hue_lifespan(server: FastMCP) -> AsyncIterator[HueContext]:
    """
    Manage connection to Hue Bridge throughout server lifespan.

    This async context manager handles:
    1. Loading saved configuration or discovering bridge
    2. Authenticating with the bridge (requires link button on first run)
    3. Building and caching light information
    4. Saving configuration for future runs

    Args:
        server: The FastMCP server instance

    Yields:
        HueContext object containing bridge connection and light cache

    Raises:
        Exception: If bridge cannot be discovered, configured, or connected
    """
    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Load saved config if it exists
    bridge_ip = BRIDGE_IP
    bridge_username = None

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                bridge_ip = config.get('bridge_ip', bridge_ip)
                bridge_username = config.get('username')
                logger.info(f"Loaded configuration from {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    # Initialize Bridge
    try:
        # If no IP specified, attempt discovery
        if not bridge_ip:
            logger.info("No bridge IP specified, attempting discovery...")
            bridge_ip = discover_bridge()
            if not bridge_ip:
                raise Exception("Bridge discovery failed. Please set BRIDGE_IP manually.")
            logger.info(f"Discovered bridge at {bridge_ip}")
        else:
            logger.info(f"Using bridge at {bridge_ip}")

        # If no username, need to create one (requires link button press)
        if not bridge_username:
            logger.error("No username found in config!")
            logger.error("=" * 60)
            logger.error("SETUP REQUIRED:")
            logger.error("1. Run: python test_connection.py")
            logger.error("2. Press the link button on your Hue bridge when prompted")
            logger.error("3. This will create ~/.hue-mcp/config.json")
            logger.error("4. Then retry running the MCP server")
            logger.error("=" * 60)
            raise Exception(
                "Bridge not configured. Please run 'python test_connection.py' first "
                "and press the link button on your Hue bridge to authenticate."
            )

        # Create bridge connection
        logger.info(f"Connecting to bridge at {bridge_ip}")
        bridge = Bridge(bridge_ip, bridge_username)

        # Test the connection by fetching lights
        try:
            light_info = bridge.lights()
            logger.info(f"Successfully connected! Found {len(light_info)} lights")
        except QhueException as e:
            logger.error(f"Failed to connect to bridge: {e}")
            raise

        # Save the configuration
        with open(CONFIG_FILE, 'w') as f:
            json.dump({
                'bridge_ip': bridge_ip,
                'username': bridge_username
            }, f)
            logger.info(f"Saved configuration to {CONFIG_FILE}")

        # Initialize and yield the context
        yield HueContext(bridge=bridge, light_info=light_info)

    except Exception as e:
        logger.error(f"Error connecting to Hue bridge: {e}")
        # Re-raise to inform the server of the failure
        raise
    finally:
        # No explicit cleanup needed for bridge connection
        pass
