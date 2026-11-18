from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from collections.abc import Iterator

from langchain_core.messages import HumanMessage

from anticla.agent.graph import build_graph
from anticla.agent.nodes import set_active_llm
from anticla.tools import file_ops, terminal


class AnticlaSDK:
    """Embeddable Python interface for Anticla's coding-agent runtime."""

    def __init__(
        self,
        workspace: str | Path | None = None,
        provider: str = "nvidia",
        model: str | None = None,
    ):
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        self.provider = provider
        self.model = model
        if provider or model:
            set_active_llm(provider=provider, model_override=model)
        self._graph = build_graph()

    @contextmanager
    def _workspace_context(self) -> Iterator[None]:
        previous_file_workspace = file_ops.WORKSPACE_PATH
        previous_terminal_workspace = terminal.WORKSPACE_PATH
        self.workspace.mkdir(parents=True, exist_ok=True)
        file_ops.WORKSPACE_PATH = self.workspace
        terminal.WORKSPACE_PATH = self.workspace
        try:
            yield
        finally:
            file_ops.WORKSPACE_PATH = previous_file_workspace
            terminal.WORKSPACE_PATH = previous_terminal_workspace

    def run_task(self, prompt: str, session_id: str | None = None) -> str:
        """Execute a coding or research task and return the final response."""
        thread_id = session_id or f"sdk-{uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        with self._workspace_context():
            result = self._graph.invoke(
                {"messages": [HumanMessage(content=prompt)]},
                config=config,
            )
        return str(result["messages"][-1].content)