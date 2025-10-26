# Philips Hue MCP Server - Setup Guide

## Quick Start (2 Steps)

### Step 1: Authenticate with Your Hue Bridge

The MCP server requires authentication with your Hue bridge. Run the setup script:

```bash
cd /Users/cstar/Développements/mcp/hue-mcp
source .venv/bin/activate
python test_connection.py
```

**When prompted:**
1. **Press the physical link button** on your Hue bridge (the round button on top)
2. Press Enter in the terminal within 30 seconds
3. The script will create `~/.hue-mcp/config.json` with your authentication credentials

**What you'll see:**
```
🔍 Testing Hue Bridge Connection with qhue...
📍 Bridge IP: 192.168.1.10

============================================================
⚠️  No username found - need to register with bridge
PRESS THE LINK BUTTON ON YOUR HUE BRIDGE NOW!
============================================================
Press Enter after pressing the link button...

✓ Created new username: abc123def4...
✓ Saved configuration to /Users/cstar/.hue-mcp/config.json
✓ Successfully connected!
💡 Found X lights
```

### Step 2: Test the MCP Server

Once authenticated, test the MCP server with the inspector:

```bash
mcp dev hue_server.py
```

This will:
- Start the MCP server in development mode
- Open the MCP Inspector in your browser
- Allow you to test all the tools interactively

Or install in Claude Desktop:

```bash
mcp install hue_server.py --name "Philips Hue"
```

## Troubleshooting

### Error: "Bridge not configured"

**Symptom:** MCP server fails with error about missing username

**Solution:** Run `python test_connection.py` first to create authentication credentials

### Error: "Connection refused" or "Bridge not found"

**Symptom:** Cannot connect to bridge

**Solution:**
1. Verify your bridge IP is correct in `hue_server.py` (line 34)
2. Make sure bridge is on same network as your computer
3. Try accessing `http://192.168.1.10` in your browser (should show Hue API)

### Error: "Link button not pressed"

**Symptom:** Authentication fails during `test_connection.py`

**Solution:**
1. Make sure you press the **physical button on the bridge** (not in the app)
2. You have 30 seconds after pressing the button
3. The button is the round button on top of the bridge

### Error: "invalid value for parameter devicetype"

**Symptom:** Error like `QhueException: 7 -> invalid value, qhue#1.0.0...ip6.arpa`

**Cause:** Your computer's hostname is too long (often IPv6 reverse DNS)

**Solution:** ✅ FIXED - Script now uses `"hue-mcp-server"` as device type instead of hostname

### "Unexpected end of JSON input" Error

**Symptom:** MCP Inspector shows JSON parsing error

**Cause:** This was caused by `print()` statements contaminating stdout

**Status:** ✅ FIXED - All `print()` statements removed from authentication flow

## Configuration File

The authentication credentials are stored in:
```
~/.hue-mcp/config.json
```

Format:
```json
{
  "bridge_ip": "192.168.1.10",
  "username": "your-auth-token-here"
}
```

To reset/re-authenticate:
```bash
rm ~/.hue-mcp/config.json
python test_connection.py
```

## Bridge IP Configuration

By default, the bridge IP is set to `192.168.1.10` (line 34 in `hue_server.py`).

### Option 1: Use Your Bridge IP
If you know your bridge IP, update line 34:
```python
BRIDGE_IP = "192.168.1.10"  # Your actual bridge IP
```

### Option 2: Enable Auto-Discovery
To discover the bridge automatically:
```python
BRIDGE_IP = None  # Enables auto-discovery
```

**Note:** Auto-discovery uses the Hue cloud discovery API and requires internet access.

## What Happens During Setup

1. **Discovery/Connection**: Script connects to bridge using configured or discovered IP
2. **Authentication**: If no credentials exist, prompts for link button press
3. **Credential Creation**: Uses qhue to create a new username (auth token)
4. **Credential Storage**: Saves bridge IP and username to `~/.hue-mcp/config.json`
5. **Verification**: Tests connection by fetching lights, groups, and scenes
6. **Ready**: MCP server can now start using saved credentials

## Development Workflow

```bash
# Initial setup (once)
python test_connection.py

# Development
mcp dev hue_server.py

# Or run server directly
python hue_server.py

# Or install in Claude Desktop
mcp install hue_server.py
```

## Security Note

The authentication token in `~/.hue-mcp/config.json` grants full control over your Hue lights. Keep it secure!

- Token is stored locally only
- No cloud service involved (except initial discovery if enabled)
- All communication is local network only
