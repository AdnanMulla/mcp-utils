import json
import asyncio
import httpx

MCP_URL = "http://127.0.0.1:8001/mcp"


async def get_session_id():
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }

    initialize_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "ExampleClient",
                "version": "1.0.0"
            }
        }
    }

    async with httpx.AsyncClient(timeout=None) as client:
        print("[1] Connecting to MCP server for initialization...")
        async with client.stream("POST", MCP_URL, headers=headers, content=json.dumps(initialize_payload)) as response:
            print("[2] Connected, streaming events...")
            # Get sessionId from response headers
            session_id = response.headers.get("mcp-session-id")
            if session_id:
                print("[2] Session initialized!")
                return session_id
            else:
                print("[X] No sessionId found in headers.")

if __name__ == "__main__":
    session_id = asyncio.run(get_session_id())
    print("Final sessionId:", session_id)
