from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from anticla.tools import execute_bash, list_files, read_file
from anticla.agent.subagent.system_prompt import (
	EXPLORER_SYSTEM_PROMPT,
	REVIEWER_SYSTEM_PROMPT,
)


def _active_model():
	"""Resolve the main agent's current model without creating an import cycle."""
	from anticla.agent.nodes import llm

	return llm


def _run_isolated_subagent(
	system_prompt: SystemMessage,
	task: str,
	tools: list,
	recursion_limit: int = 12,
) -> str:
	"""Run an isolated, stateless LangGraph subagent and return its final report."""
	bound_llm = _active_model().bind_tools(tools)

	def subagent_node(state: MessagesState) -> dict:
		messages = [system_prompt] + list(state["messages"])
		response = bound_llm.invoke(messages)
		return {"messages": [response]}

	builder = StateGraph(MessagesState)
	builder.add_node("worker", subagent_node)
	builder.add_node("tools", ToolNode(tools))
	builder.add_edge(START, "worker")
	builder.add_conditional_edges("worker", tools_condition)
	builder.add_edge("tools", "worker")

	sub_graph = builder.compile()

	try:
		result = sub_graph.invoke(
			{"messages": [HumanMessage(content=task)]},
			config={"recursion_limit": recursion_limit},
		)
		final_msg = result["messages"][-1]
		return str(final_msg.content) or "Subagent completed with no text output."
	except Exception as exc:
		return f"Subagent execution error ({type(exc).__name__}): {exc}"


@tool
def delegate_research(task: str) -> str:
	"""Delegate codebase exploration to an isolated read-only Explorer subagent."""
	return _run_isolated_subagent(
		system_prompt=EXPLORER_SYSTEM_PROMPT,
		task=task,
		tools=[list_files, read_file],
		recursion_limit=12,
	)


@tool
def delegate_review(task: str) -> str:
	"""Delegate code review and verification to an isolated QA Reviewer subagent."""
	return _run_isolated_subagent(
		system_prompt=REVIEWER_SYSTEM_PROMPT,
		task=task,
		tools=[list_files, read_file, execute_bash],
		recursion_limit=12,
	)
