import asyncio
from fastmcp import Client, FastMCP
import json

# In-memory server (ideal for testing)
server = FastMCP("TestServer")
client = Client(server)

# HTTP server
client = Client("http://localhost:8000/test/mcp")


async def main():
    async with client:
        # Basic server interaction
        await client.ping()

        # List available operations
        tools = await client.list_tools()
        for tool in tools:
            print(tool.name, "\n", tool.description)
            print("Parameters:\n", json.dumps(tool.inputSchema, indent=2))
            print("Output:\n", json.dumps(tool.outputSchema, indent=2))

        # print("Available tools:\n", json.dumps(tools, indent=2))
        # resources = await client.list_resources()
        # print("Available resources:\n", json.dumps(resources, indent=2))
        # prompts = await client.list_prompts()
        # print("Available prompts:\n", json.dumps(prompts, indent=2))
        # Execute operations
        result = await client.call_tool(
            "save_file", {"file_path": "test.txt", "content": "Hello, World!"}
        )
        print(result)


asyncio.run(main())
