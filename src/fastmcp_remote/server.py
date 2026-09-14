from fastmcp import FastMCP

mcp = FastMCP("My Remote Server")


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@mcp.tool
def hello(name: str) -> str:
    """Say hello to a person."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
