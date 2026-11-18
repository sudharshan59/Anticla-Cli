from pathlib import Path
from langchain_core.tools import tool
from rich.prompt import Confirm
from anticla.core.config import WORKSPACE_PATH

def _safe_resolve(filepath: str, operation: str) -> Path:
    """Resolve a path and request approval when it leaves the workspace."""
    target = (WORKSPACE_PATH / filepath).resolve()
    if not target.is_relative_to(WORKSPACE_PATH):
        approved = Confirm.ask(
            f"Allow {operation} outside the sandbox? [cyan]{target}[/cyan]",
            default=False,
        )
        if not approved:
            raise PermissionError(f"Access denied: {filepath} is outside the sandbox workspace.")
    return target

@tool
def list_files(directory: str = ".") -> str:
    """Lists all files and folders inside a workspace directory."""
    try:
        target = _safe_resolve(directory, "listing")
        if not target.exists():
            return f"Directory not found: {directory}"
        items = [p.name + ("/" if p.is_dir() else "") for p in target.iterdir()]
        return "\n".join(items) if items else "(Empty directory)"
    except Exception as e:
        return f"Error listing files: {str(e)}"

@tool
def read_file(filepath: str) -> str:
    """Reads the text content of a file in the workspace."""
    try:
        target = _safe_resolve(filepath, "reading")
        if not target.is_file():
            return f"File not found: {filepath}"
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"

@tool
def write_file(filepath: str, content: str) -> str:
    """Writes or overwrites a file in the workspace with the provided content."""
    try:
        target = _safe_resolve(filepath, "writing")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} characters to {filepath}"
    except Exception as e:
        return f"Error writing file: {str(e)}"