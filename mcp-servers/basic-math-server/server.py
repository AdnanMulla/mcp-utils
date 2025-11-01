# server.py
from fastmcp import FastMCP

mcp = FastMCP("BasicMathServer")

# Tools


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers."""
    return a + b


@mcp.tool()
def subtract(a: float, b: float) -> float:
    """Subtract b from a."""
    return a - b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers."""
    return a * b


@mcp.tool()
def divide(a: float, b: float) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Division by zero is not allowed.")
    return a / b


@mcp.tool()
def power(a: float, b: float) -> float:
    """Raise a to the power of b (a^b)."""
    return a ** b


@mcp.tool()
def average(numbers: list[float]) -> float:
    """Return the average of a list of numbers."""
    if not numbers:
        raise ValueError("List cannot be empty.")
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    # Run HTTP transport on localhost, port 8000, path /mcp
    print("STARTING server...")
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")
