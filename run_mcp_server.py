# coding: utf-8
# A shortcut to launch OpenManus MCP server, where its introduction also solves other import issues.
import os
from app.mcp.server import MCPServer, parse_args
from app.db import init_db
from app.db.tool_registry import tool_registry


if __name__ == "__main__":
    args = parse_args()

    # Ensure data directory exists
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

    # Initialize database tables
    init_db()

    # Create server
    server = MCPServer()

    # Register job engine tools with server
    tool_registry.register_with_server(server)

    # Run server
    server.run(transport=args.transport)
