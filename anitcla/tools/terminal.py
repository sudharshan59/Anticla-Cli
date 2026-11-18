import subprocess
from rich.console import Console
from rich.prompt import Confirm
from langchain_core.tools import tool
from anticla.core.config import WORKSPACE_PATH

console = Console()

@tool
def execute_bash(command: str) -> str:
    """Executes a shell command inside the workspace directory after user approval."""
    console.print(f"\n[bold yellow]⚠ Anticla wants to execute:[/bold yellow] [cyan]{command}[/cyan]")
    
    # Human-in-the-loop safety gate
    approved = Confirm.ask("Allow this command to run?", default=False)
    if not approved:
        return "Execution aborted: The user denied permission to run this command."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(WORKSPACE_PATH),
            capture_output=True,
            text=True,
            timeout=60
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if not output:
            return f"Command completed with exit code {result.returncode} (no output)."
        return "\n".join(output)
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        return f"Execution error: {str(e)}"