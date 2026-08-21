from __future__ import annotations

import os
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from .prompts import SYSTEM_PROMPT, WELCOME_PROMPT
from .tools import TOOLS


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3:latest")


def _build_model() -> ChatOllama:
    model = ChatOllama(
        model=MODEL_NAME,
        temperature=0,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )
    return model.bind_tools(TOOLS)


LLM_WITH_TOOLS = _build_model()


def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
    """Ask the model either for the next tool call or for the final user-facing answer."""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        SystemMessage(content=WELCOME_PROMPT),
        *state["messages"],
    ]
    response = LLM_WITH_TOOLS.invoke(messages)
    return {"messages": [response]}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("assistant", call_model)
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "assistant")
    graph.add_conditional_edges("assistant", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")
    return graph.compile()


AGENT_GRAPH = build_graph()


def run_agent(student_id: str, user_message: str) -> tuple[str, list[str]]:
    """Run one bounded conversation turn and return the final answer plus a lightweight trace."""
    initial_message = HumanMessage(
        content=f"Student ID: {student_id}\nUser request: {user_message}"
    )
    result = AGENT_GRAPH.invoke(
        {"messages": [initial_message]},
        config={"recursion_limit": 12},
    )

    final_answer = "I could not produce an answer. Please try again with a course ID."
    trace: list[str] = []
    for message in result["messages"]:
        if isinstance(message, AIMessage):
            if message.tool_calls:
                trace.extend(call["name"] for call in message.tool_calls)
            elif message.content:
                final_answer = str(message.content)

    return final_answer, trace
