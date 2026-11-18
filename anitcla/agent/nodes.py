import os
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"Found .* in available_models, but type is unknown and inference may fail\.",
    module=r"langchain_nvidia_ai_endpoints\..*",
)
warnings.filterwarnings(
    "ignore",
    message=r"Model .* is not known to support tools\. Your tool binding may fail at inference time\.",
    module=r"langchain_nvidia_ai_endpoints\..*",
)

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.prebuilt import ToolNode
from anticla.agent.state import IDEState
from anticla.agent.system_prompt import SYSTEM_PROMPT
from anticla.core.config import settings
from anticla.tools import ide_tools

os.environ["NVIDIA_API_KEY"] = settings.nvidia_api_key

def _build_llm(provider: str, model_override: str | None = None):
    if provider == "local":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model_override or settings.ollama_model_id,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )

    return ChatNVIDIA(
        model=model_override or settings.nvidia_model_id,
        api_key=settings.nvidia_api_key,
        temperature=0.1,
        max_completion_tokens=4096,
    )


llm = _build_llm(settings.llm_provider)
llm_with_tools = llm.bind_tools(ide_tools)


def set_active_llm(provider: str, model_override: str | None = None) -> None:
    """Rebuild the active model when the CLI provider or model changes."""
    global llm, llm_with_tools
    llm = _build_llm(provider, model_override)
    llm_with_tools = llm.bind_tools(ide_tools)

def coder_agent(state: IDEState) -> dict:
    """Invokes the configured LLM with the system prompt and conversation history."""
    messages = [SYSTEM_PROMPT] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_executor = ToolNode(ide_tools)