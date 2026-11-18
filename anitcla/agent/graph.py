from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from anticla.agent.nodes import coder_agent, tool_executor
from anticla.agent.state import IDEState

def route_after_agent(state: IDEState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

workflow = StateGraph(IDEState)

workflow.add_node("coder", coder_agent)
workflow.add_node("tools", tool_executor)

workflow.add_edge(START, "coder")
workflow.add_conditional_edges(
    "coder",
    route_after_agent,
    {
        "tools": "tools",
        END: END,
    },
)
workflow.add_edge("tools", "coder")

def build_graph():
    """Build a fresh compiled agent graph with in-memory checkpointing."""
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


ide_app = build_graph()