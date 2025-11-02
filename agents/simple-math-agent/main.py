import os
import logging
from dotenv import load_dotenv
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from mcp_utils import call_mcp_tool_jsonrpc, BASIC_MATH_SERVER_URL, NUMERICS_MATH_SERVER_URL, BASIC_MATH_SERVER_SESSION_ID, NUMERICS_MATH_SERVER_SESSION_ID
from system_prompt import system_prompt

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

# ---- LLM / LangGraph setup ----
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

# ---- Nodes --------
CLASSIFY_INPUT_NODE = "classify_input"
CALL_TOOL_NODE = "call_tool"
RESPOND_NODE = "respond"

# ---- Node: classify user input ----


def classify_input(state: State):
    last_message = state.get("messages")[-1]
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


graph_builder.add_node(CLASSIFY_INPUT_NODE, classify_input)

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

    state["tool_result"] = result
    return state


graph_builder.add_node(CALL_TOOL_NODE, call_tool)

# ---- Node: respond back ----


def respond(state: State):
    result = state.get("tool_result")
    return {"messages": [{"role": "assistant", "content": f"Result: {result}"}]}


graph_builder.add_node(RESPOND_NODE, respond)

# ---- Add edges -------------

graph_builder.add_edge(START, CLASSIFY_INPUT_NODE)
graph_builder.add_edge(CLASSIFY_INPUT_NODE, CALL_TOOL_NODE)
graph_builder.add_edge(CALL_TOOL_NODE, RESPOND_NODE)
graph_builder.add_edge(RESPOND_NODE, END)

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

        logging.debug(f"Agent response: {state.get("messages")[-1].content}")


print("=========================================END==================================")
