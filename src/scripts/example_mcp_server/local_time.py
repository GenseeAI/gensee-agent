from datetime import datetime
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("local_time")

@mcp.tool()
async def get_local_time() -> str:
    """Get local time information.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def main():
    # mcp.run(transport='streamable-http')
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
