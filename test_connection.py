#!/usr/bin/env python3
"""
Test script to verify Hue bridge connection with qhue
"""
import asyncio
import json
import os
from qhue import Bridge, QhueException, create_new_username

# Configuration
BRIDGE_IP = "192.168.1.10"
CONFIG_DIR = os.path.expanduser("~/.hue-mcp")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


async def test_connection():
    """Test the Hue bridge connection"""
    print("🔍 Testing Hue Bridge Connection with qhue...")
    print(f"📍 Bridge IP: {BRIDGE_IP}")

    # Ensure config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)

    # Load saved config if it exists
    bridge_username = None
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                bridge_username = config.get('username')
                print(f"✓ Loaded existing username from config")
        except Exception as e:
            print(f"✗ Error loading config: {e}")

    # Create username if needed
    if not bridge_username:
        print("\n" + "="*60)
        print("⚠️  No username found - need to register with bridge")
        print("PRESS THE LINK BUTTON ON YOUR HUE BRIDGE NOW!")
        print("="*60)
        input("Press Enter after pressing the link button...")

        try:
            # Use a custom device type instead of FQDN which can be too long
            bridge_username = create_new_username(BRIDGE_IP, devicetype="hue-mcp-server")
            print(f"✓ Created new username: {bridge_username[:10]}...")

            # Save config
            with open(CONFIG_FILE, 'w') as f:
                json.dump({
                    'bridge_ip': BRIDGE_IP,
                    'username': bridge_username
                }, f)
            print(f"✓ Saved configuration to {CONFIG_FILE}")

        except QhueException as e:
            print(f"✗ Failed to create username: {e}")
            return False

    # Create bridge connection
    print(f"\n📡 Connecting to bridge...")
    bridge = Bridge(BRIDGE_IP, bridge_username)

    # Test the connection by fetching lights
    try:
        lights = bridge.lights()
        print(f"✓ Successfully connected!")
        print(f"💡 Found {len(lights)} lights:")

        for light_id, light in lights.items():
            status = "ON" if light['state']['on'] else "OFF"
            brightness = light['state'].get('bri', 'N/A')
            print(f"  - [{light_id}] {light['name']}: {status} (brightness: {brightness})")

        # Test groups
        groups = bridge.groups()
        print(f"\n🏠 Found {len(groups)} groups:")
        for group_id, group in groups.items():
            print(f"  - [{group_id}] {group['name']}: {len(group['lights'])} lights")

        # Test scenes
        scenes = bridge.scenes()
        print(f"\n🎨 Found {len(scenes)} scenes")

        print("\n✅ All tests PASSED! qhue integration is working correctly.")
        return True

    except QhueException as e:
        print(f"✗ Failed to connect: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(test_connection())
    exit(0 if result else 1)
