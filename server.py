# server.py
from fastmcp import FastMCP

mcp = FastMCP("SimpleServer")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

if __name__ == "__main__":
    # Run HTTP transport on localhost, port 8000, path /mcp
    print("STARTING server...")
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
