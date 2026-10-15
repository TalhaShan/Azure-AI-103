# Add references
# FastMCP is a helper from the official MCP Python SDK that makes it easy
# to expose normal Python functions as MCP tools.
from mcp.server.fastmcp import FastMCP

# Create an MCP server
# The name ("Inventory") is how the server identifies itself to clients.
mcp = FastMCP("Inventory")


# Add an inventory check mcp tool
# @mcp.tool() registers the function as a tool. The function name becomes the
# tool name and the docstring becomes the description the agent's model reads
# to decide when to call it. The return type hint is used to describe output.
@mcp.tool()
def get_inventory_levels() -> dict:
    """Returns current inventory for all products."""
    return {
        "Moisturizer": 6,
        "Shampoo": 8,
        "Body Spray": 28,
        "Hair Gel": 5,
        "Lip Balm": 12,
        "Skin Serum": 9,
        "Cleanser": 30,
        "Conditioner": 3,
        "Setting Powder": 17,
        "Dry Shampoo": 45
    }


# Add a weekly sales mcp tool
@mcp.tool()
def get_weekly_sales() -> dict:
    """Returns number of units sold last week."""
    return {
        "Moisturizer": 22,
        "Shampoo": 18,
        "Body Spray": 3,
        "Hair Gel": 2,
        "Lip Balm": 14,
        "Skin Serum": 19,
        "Cleanser": 4,
        "Conditioner": 1,
        "Setting Powder": 13,
        "Dry Shampoo": 17
    }


# Run the MCP server
# "stdio" transport means the server talks over standard input/output.
# client.py launches this file as a subprocess and communicates through it,
# so you never need to start server.py yourself.
if __name__ == "__main__":
    mcp.run(transport="stdio")