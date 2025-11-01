import os
import logging
from dotenv import load_dotenv
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


print("=========================================START================================")

CLASSIFIER_NODE = "classifier"
ROUTER_NODE = "router"
THERAPIST_NODE = "therapist"
LOGICAL_NODE = "logical"

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

llm = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_genai"
)


class MessageClassifier(BaseModel):
    message_type: Literal["emotional", "logical"] = Field(
        ..., description="Classify if the message requires an emotional (therapist) or logical response.")


class State(TypedDict):
    messages: Annotated[list, add_messages]
    message_type: str | None
    next: str | None


def classify_message(state: State):
    logging.debug("START - classify_message")
    logging.debug("Input: ", state)

    last_message = state["messages"][-1]

    classifier_llm = llm.with_structured_output(MessageClassifier)

    result = classifier_llm.invoke(
        [
            {
                "role": "system",
                "content": """Classify the user message as either:
                            - 'emotional': if it asks for emotional support, therapy, deals with feelings, or personal problems
                            - 'logical': if it asks for facts, information, logical analysis, or practical solutions
                            """
            },
            {"role": "user", "content": last_message.content}
        ])

    output = {"message_type": result.message_type}

    logging.debug("Output: ", output)
    logging.debug("END - classify_message")
    return output


def route_message(state: State):
    logging.debug("START - route_message")
    logging.debug("Input: ", state)
    message_type = state.get("message_type", LOGICAL_NODE)

    if message_type == "emotional":
        return {"next": THERAPIST_NODE}

    output = {"next": LOGICAL_NODE}

    logging.debug("Output: ", output)
    logging.debug("END - route_message")
    return output


def therapist_agent(state: State):
    logging.debug("START - therapist_agent")
    logging.debug("Input: ", state)
    last_message = state["messages"][-1]

    messages = [
        {
            "role": "system",
            "content": """You are a compassionate therapist. Focus on the emotional aspects of the user's message.
                        Show empathy, validate their feelings, and help them process their emotions.
                        Ask thoughtful questions to help them explore their feelings more deeply.
                        Avoid giving logical solutions unless explicitly asked."""
        },
        {
            "role": "user",
            "content": last_message.content
        }
    ]

    result = llm.invoke(messages)

    output = {"messages": [{"role": "assistant", "content": result.content}]}

    logging.debug("Output: ", output)
    logging.debug("END - route_message")
    return output


def logical_agent(state: State):
    logging.debug("START - logical_agent")
    logging.debug("Input: ", state)
    last_message = state["messages"][-1]

    messages = [
        {
            "role": "system",
            "content": """You are a purely logical assistant. Focus only on facts and information.
                    Provide clear, concise answers based on logic and evidence.
                    Do not address emotions or provide emotional support.
                    Be direct and straightforward in your responses."""
        },
        {
            "role": "user",
            "content": last_message.content
        }
    ]

    result = llm.invoke(messages)
    output = {"messages": [{"role": "assistant", "content": result.content}]}

    logging.debug("Output: ", output)
    logging.debug("END - logical_agent")
    return output


graph_builder = StateGraph(State)

# Add nodes
graph_builder.add_node(CLASSIFIER_NODE, classify_message)
graph_builder.add_node(ROUTER_NODE, route_message)
graph_builder.add_node(THERAPIST_NODE, therapist_agent)
graph_builder.add_node(LOGICAL_NODE, logical_agent)

# Add edges
graph_builder.add_edge(START, CLASSIFIER_NODE)
graph_builder.add_edge(CLASSIFIER_NODE, ROUTER_NODE)
graph_builder.add_conditional_edges(
    ROUTER_NODE,
    lambda state: state.get("next"),
    {"therapist": THERAPIST_NODE, "logical": LOGICAL_NODE}
)
graph_builder.add_edge(THERAPIST_NODE, END)
graph_builder.add_edge(LOGICAL_NODE, END)

graph = graph_builder.compile()


def run_bot():
    logging.info("START - BOT")
    state = {"messages": [], "message_type": None}

    while True:
        user_input = input("Enter a message: ")
        if user_input.lower() == "exit":
            print("You chose to exit. See you later !!")
            break

        state["messages"] = state.get("messages", []) + [
            {"role": "user", "content": user_input}
        ]

        state = graph.invoke(state)

        if state.get("messages") and len(state.get("messages")) > 0:
            last_message = state["messages"][-1]
            print(f"Assistant response: {last_message.content}")

    logging.info("END - BOT")


if __name__ == "__main__":
    run_bot()

    print(
        "=========================================END==================================")
