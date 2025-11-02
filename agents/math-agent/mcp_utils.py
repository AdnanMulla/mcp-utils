import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()

BASIC_MATH_SERVER_URL = os.getenv("BASIC_MATH_SERVER_URL", "")
NUMERICS_MATH_SERVER_URL = os.getenv("NUMERICS_MATH_SERVER_URL", "")


BASIC_MATH_SERVER_SESSION_ID = os.getenv("BASIC_MATH_SERVER_SESSION_ID", "")
NUMERICS_MATH_SERVER_SESSION_ID = os.getenv(
    "NUMERICS_MATH_SERVER_SESSION_ID", "")


def call_mcp_tool_jsonrpc(server_url: str, tool_name: str, arguments: dict):
    session_id = BASIC_MATH_SERVER_SESSION_ID if server_url == BASIC_MATH_SERVER_URL else NUMERICS_MATH_SERVER_SESSION_ID
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Mcp-Session-Id": session_id
    }
    response = requests.post(server_url, json=payload, headers=headers)
    response.raise_for_status()

    # Parse SSE-style response
    for line in response.text.splitlines():
        if line.startswith("data:"):
            json_data = line[len("data:"):].strip()
            data = json.loads(json_data)
            if "result" in data:
                # The actual tool result is nested under structuredContent.result
                return data["result"].get("structuredContent", {}).get("result")
            elif "error" in data:
                raise Exception(f"MCP Error: {data['error']}")
    raise Exception(f"No valid result found in MCP response: {response.text}")
