import requests
import os
import logging
import json
from dotenv import load_dotenv
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

print("=========================================START================================")

load_dotenv()

# 1️⃣ Read the log level from an environment variable (default: INFO)
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

# 2️⃣ Convert to a logging level (defaults to INFO if invalid)
log_level = getattr(logging, log_level_str, logging.INFO)

# 3️⃣ Configure logging
logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


BASIC_MATH_SERVER_URL = "http://127.0.0.1:8000/mcp"
NUMERICS_MATH_SERVER_URL = "http://127.0.0.1:8001/mcp"

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


# ---- LLM / LangGraph setup ----
system_prompt = """
You are an assistant that maps user math queries to MCP tool calls.
Output **strict JSON** only matching this structure:

{
  "server": "basic_math" | "number_theory",
  "tool": "add" | "subtract" | "gcd" | "lcm",
  "arguments": {
    "a": number,
    "b": number
  }
}

Rules:
1. Extract numeric values from the query into a and b.
2. Always include both a and b as numbers.
3. Do NOT return any text other than the JSON.
4. Examples:
- "gcd of 4 and 12" → {"server":"number_theory","tool":"gcd","arguments":{"a":4,"b":12}}
- "add 3 and 5" → {"server":"basic_math","tool":"add","arguments":{"a":3,"b":5}}
"""


llm = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_genai",
)

# ---- Structured output for classification ----


class Arguments(BaseModel):
    a: float
    b: float


class TaskClassifier(BaseModel):
    server: Literal["basic_math",
                    "number_theory"] = Field(..., description="Which MCP server to use.")
    tool: Literal["add", "subtract", "gcd",
                  "lcm"] = Field(..., description="The specific tool to call.")
    arguments: Arguments

# ---- State definition ----


class State(TypedDict):
    messages: Annotated[list, add_messages]
    classification: TaskClassifier
    tool_result: str | None


graph_builder = StateGraph(State)

# ---- Node: classify user input ----


def classify_input(state: State):
    last_message = state["messages"][-1]
    classifier_llm = llm.with_structured_output(TaskClassifier)

    try:
        classification: TaskClassifier = classifier_llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": last_message.content}
        ])
    except Exception as e:
        logging.error(f"LLM classification failed: {e}")
        raise

    state["classification"] = classification.model_dump()
    return state


graph_builder.add_node("classify_input", classify_input)

# ---- Node: call MCP tool ----


def call_tool(state: State):
    task_dict = state.get("classification")
    if not task_dict:
        raise ValueError("Classification missing in state")

    task = TaskClassifier(**task_dict)
    if not task.arguments:
        raise ValueError(f"Arguments missing in classification: {task}")

    if task.server == "basic_math":
        server_url = BASIC_MATH_SERVER_URL
    else:
        server_url = NUMERICS_MATH_SERVER_URL

    arguments_dict = task.arguments.model_dump()
    result = call_mcp_tool_jsonrpc(server_url, task.tool, arguments_dict)
    return {"tool_result": result}


graph_builder.add_node("call_tool", call_tool)

# ---- Node: respond back ----


def respond(state: State):
    result = state["tool_result"]
    return {"messages": [{"role": "assistant", "content": f"Result: {result}"}]}


graph_builder.add_node("respond", respond)

# ---- Add edges -------------

graph_builder.add_edge(START, "classify_input")
graph_builder.add_edge("classify_input", "call_tool")
graph_builder.add_edge("call_tool", "respond")
graph_builder.add_edge("respond", END)

# ---- Compile graph --------

graph = graph_builder.compile()

# ----- Agent in action ------

if __name__ == "__main__":
    if not BASIC_MATH_SERVER_SESSION_ID or not NUMERICS_MATH_SERVER_SESSION_ID:
        logging.error(
            "Cannot proceed without session-ids. Please set them in the .env file")
    else:
        user_input = input("Enter your query: ")

        state = graph.invoke(
            {"messages": [{"role": "user", "content": user_input}]})

        logging.debug(f"Agent response: {state["messages"][-1].content}")


print("=========================================END==================================")
