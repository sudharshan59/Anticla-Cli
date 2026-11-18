from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class IDEState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]