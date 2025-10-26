# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Philips Hue MCP (Model Context Protocol) Server** that provides an AI-friendly interface for controlling Philips Hue smart lights. Built with Python 3.13+ and the FastMCP framework, it exposes lights, groups, and scenes as MCP resources and tools.

## Key Architecture Concepts

### MCP Server Structure
- **Entry Point**: `hue_server.py` - Main FastMCP server implementation
- **Bridge Connection**: Uses `qhue` library (not `phue` as mentioned in docs) for Philips Hue API
- **Lifespan Management**: `hue_lifespan()` async context manager handles bridge initialization and cleanup
- **Context Object**: `HueContext` dataclass holds bridge connection and light info cache

### Core Components Flow
1. **Startup**: Server connects to bridge (auto-discovery or configured IP) → authenticates → caches light info
2. **Runtime**: Tools/resources access bridge via `get_bridge_ctx(ctx)` helper
3. **State Management**: Light info cached in context, refreshable via `refresh_lights()` tool

### Configuration System
- **Config Location**: `~/.hue-mcp/config.json` (auto-created on first run)
- **Config Contents**: Bridge IP and username (auth token)
- **Bridge IP**: Default is `"192.168.1.10"` in code (line 33) - can be set to `None` for auto-discovery
- **First Run**: Requires pressing link button on physical Hue bridge for authentication

### Color Space Conversion
- Hue uses CIE XY color space, not RGB
- `rgb_to_xy()` utility (lines 137-170) converts RGB → XY with gamma correction
- Wide RGB D65 conversion matrix used for accurate color representation

## Development Commands

### Environment Setup
```bash
# Install dependencies (uses uv package manager)
uv sync

# Activate virtual environment
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows
```

### Running the Server

```bash
# Development mode with MCP Inspector (best for testing)
mcp dev hue_server.py

# Direct execution (starts uvicorn server)
python hue_server.py

# Custom host/port/logging
python hue_server.py --host 0.0.0.0 --port 8888 --log-level debug

# Install in Claude Desktop
mcp install hue_server.py --name "My Hue Lights"
```

### Testing Tools
```bash
# MCP Inspector for interactive testing
mcp dev hue_server.py

# Direct server run (accessible at http://127.0.0.1:8080 by default)
python hue_server.py
```

## Important Implementation Details

### Tool vs Resource Pattern
- **Resources** (`@mcp.resource`): Read-only data access (lights, groups, scenes info)
  - Converted to tools in this implementation (lines 199-326)
  - Should be fast, no side effects
- **Tools** (`@mcp.tool`): Actions that change state (turn on/off, set colors)
  - All require `ctx: Context` parameter to access bridge
  - Should validate IDs before operations

### Validation Pattern
- **Light IDs**: Use `validate_light_id(light_id, light_info)` before operations
- **Group IDs**: Use `validate_group_id(group_id, bridge)` before operations
- **Scene IDs**: Check against `bridge.get_scene()` results
- **Always return error messages** instead of raising exceptions for better UX

### Brightness Scale
- Hue API uses 0-254 scale (not 0-255!)
- Convert to percentage: `round((brightness / 254) * 100)`
- Always turn light on before setting brightness if currently off

### Color Temperature
- Valid range: 2000K-6500K
- Convert to mired: `mired = int(1000000 / temperature)`
- Use `ct` parameter on bridge, not direct Kelvin values

### Group 0 Special Case
- Group 0 typically represents "All lights"
- Always available, used as default in `quick_scene()` tool

## Code Modification Guidelines

### Adding New Tools
1. Decorate with `@mcp.tool()`
2. Include `ctx: Context` parameter
3. Get bridge via `bridge, light_info = get_bridge_ctx(ctx)`
4. Validate inputs (IDs, ranges) before API calls
5. Return descriptive strings (success/error messages)
6. Use try/except with logging for error handling

### Adding New Resources
1. Decorate with `@mcp.resource("uri://pattern")`
2. Return JSON strings (use `json.dumps(data, indent=2)`)
3. Format data for readability before returning
4. Handle missing data gracefully

### Bridge State Updates
- Bridge connection persists in lifespan context
- Light info cache updated on startup and via `refresh_lights()`
- For real-time state: call `bridge.get_light()` or `bridge.get_api()`
- Update context cache: `ctx.request_context.lifespan_context.light_info = new_info`

### Error Handling Pattern
```python
try:
    # Validate
    if not validate_light_id(light_id, light_info):
        return f"Error: Light with ID {light_id} not found."

    # Execute
    bridge.set_light(light_id, 'on', True)

    # Return success with details
    return f"Light {light_id} ({light_info[str(light_id)]['name']}) turned on."
except Exception as e:
    logger.error(f"Error turning on light {light_id}: {e}")
    return f"Error: {str(e)}"
```

## Configuration Notes

### Bridge IP Discovery
- If `BRIDGE_IP = None`: Server attempts auto-discovery via `Bridge()` constructor
- If discovery fails: User must manually set IP in code or `~/.hue-mcp/config.json`
- Bridge IP can be found via Hue app or router DHCP list

### Authentication Flow
1. First run: Server prompts to press link button
2. User presses button (30-second window)
3. Server creates username (auth token)
4. Credentials saved to `~/.hue-mcp/config.json`
5. Subsequent runs: Auto-authenticate with saved credentials

### Troubleshooting Config
- **Delete config to re-auth**: `rm ~/.hue-mcp/config.json`
- **Manual config creation**:
  ```bash
  mkdir -p ~/.hue-mcp
  echo '{"bridge_ip": "192.168.1.x"}' > ~/.hue-mcp/config.json
  ```

## Testing Approach

### Quick Validation
1. Start server: `mcp dev hue_server.py`
2. Check resources load without errors
3. Test basic tool: `get_all_lights`
4. Test state change: `turn_on_light` with valid ID
5. Verify error handling: Invalid light ID

### Integration Testing
- Test with actual Hue hardware required (no mock mode)
- Bridge must be on same network as development machine
- Verify all light types (color, temperature, dimmable only) work correctly

## Dependencies

- **mcp[cli]** (≥1.5.0): FastMCP framework for MCP server implementation
- **qhue** (≥1.0): Philips Hue API client library (lightweight, modern wrapper)
- **requests**: HTTP library (used for bridge discovery and group creation)
- **Python** 3.13+: Required for modern type hints and async features

### Why qhue instead of phue?
- **qhue**: Lightweight, modern, follows Hue API structure directly
- **phue**: Older library with different abstraction layer
- The port from phue to qhue was completed to use a more actively maintained library

## Common Pitfalls

1. **BRIDGE_IP hardcoded**: Line 34 has user's actual bridge IP - set to `None` for auto-discovery if needed
2. **qhue API differences**:
   - Use `bridge.lights()` not `bridge.get_light()`
   - Use `bridge.lights[str(id)](on=True)` not `bridge.set_light(id, 'on', True)`
   - Use `bridge.groups[str(id)].action(on=True)` for group control
3. **Light ID strings**: Bridge API returns string keys, must convert `str(light_id)` for dict lookups
4. **Color capability**: Not all lights support `xy` (color) or `ct` (temperature) - always check before setting
5. **Brightness range**: 0-254, not 0-255 or 0-100
6. **Context access**: Must use `ctx.request_context.lifespan_context` to get `HueContext`
7. **Physical button required**: First-time auth requires pressing the link button on the physical Hue bridge

## Extension Points

- **New presets**: Add to `presets` dict in `set_color_preset()` (line 812-830)
- **Custom effects**: Use `bridge.set_light(id, 'effect', value)` for new effects
- **Scenes**: Create persistent scenes via `bridge.create_scene()` (not currently implemented)
- **Schedules**: Would require Hue app, not controllable via this MCP interface
- **Sensors/Motion**: Bridge API supports these, could add as resources
