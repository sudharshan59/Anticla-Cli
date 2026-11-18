import difflib
import shutil
import time
from pathlib import Path
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm
from rich.rule import Rule
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl

console = Console()

COLOR_ACCENT = "cyan"
COLOR_SUCCESS = "green"
COLOR_WARNING = "yellow"
COLOR_ERROR = "red"
COLOR_MUTED = "bright_black"


class ParallelPromptSession(PromptSession):
    """PromptSession that frames the active input line between live parallel divider lines."""

    def _create_layout(self):
        layout = super()._create_layout()
        float_container = layout.container.children[0].alternative_content
        inner_hsplit = float_container.content

        def get_bottom_line():
            width = shutil.get_terminal_size(fallback=(80, 24)).columns
            return [("ansibrightblack", "─" * max(1, width - 2))]

        bottom_window = Window(
            content=FormattedTextControl(get_bottom_line),
            height=1,
            dont_extend_height=True,
        )
        inner_hsplit.children.append(bottom_window)
        return layout


prompt_session: ParallelPromptSession | None = None


def get_prompt_session() -> PromptSession:
    """Lazily instantiate the session to avoid startup crashes in headless environments."""
    global prompt_session
    if prompt_session is None:
        try:
            prompt_session = ParallelPromptSession()
        except Exception:
            from prompt_toolkit.input import DummyInput
            from prompt_toolkit.output import DummyOutput

            prompt_session = ParallelPromptSession(input=DummyInput(), output=DummyOutput())
    return prompt_session


def render_banner(provider: str, model: str, workspace: Path) -> None:
    """Render the startup header with workspace and model metadata."""
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_row(
        "[bold cyan]ANTICLA[/bold cyan] [dim]v0.1.0 | Agentic Coding CLI[/dim]",
    )
    grid.add_row(
        f"[dim]Provider:[/dim] [white]{provider}[/white]",
    )
    grid.add_row(
        f"[dim]Model:[/dim] [white]{model}[/white]",
    )
    grid.add_row(
        f"[dim]Workspace:[/dim] [yellow]{workspace}[/yellow]",
    )
    grid.add_row(
        "[dim]Commands: [bold]/help[/bold] for help | [bold]exit[/bold] to quit[/dim]",
    )
    console.print(Panel(grid, border_style="cyan", padding=(0, 1)))


def print_banner() -> None:
    """Render the default CLI header used by the interactive command."""
    from anticla.core.config import WORKSPACE_PATH, settings

    active_model = (
        settings.ollama_model_id
        if settings.llm_provider == "local"
        else settings.nvidia_model_id
    )
    render_banner(settings.llm_provider, active_model, WORKSPACE_PATH)


def render_help() -> None:
    """Display available REPL slash commands."""
    table = Table(title="Anticla REPL Commands", border_style="bright_black", show_header=True)
    table.add_column("Command", style="bold cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_row("/help", "Show this command menu")
    table.add_row("/clear", "Reset conversation memory (start fresh thread)")
    table.add_row("/model <id>", "Hot-swap active model ID (e.g., qwen/qwen2.5-coder-32b-instruct)")
    table.add_row("/provider <nvidia|local>", "Switch between NVIDIA NIM and local Ollama")
    table.add_row("exit / quit", "Close the interactive session")
    console.print(table)


def get_user_input() -> str:
    """Render the user input enclosed between live parallel horizontal lines."""
    console.print()

    def get_prompt_text() -> HTML:
        width = shutil.get_terminal_size(fallback=(80, 24)).columns
        divider = "─" * max(1, width - 2)
        return HTML(f"<ansibrightblack>{divider}</ansibrightblack>\n<ansicyan>></ansicyan> ")

    session = get_prompt_session()
    return session.prompt(get_prompt_text).strip()


def render_turn_separator(label: str = "") -> None:
    """Visually delimit one complete agent turn from the next."""
    console.print()
    console.print(Rule(label, style=COLOR_MUTED))


def render_tool_call(tool_name: str, args: dict) -> None:
    """Render structured tool execution cards instead of raw dicts."""
    if tool_name == "write_file":
        filepath = args.get("filepath", "unknown")
        content = args.get("content", "")
        ext = Path(filepath).suffix.lstrip(".") or "python"
        preview = "\n".join(content.splitlines()[:25])
        if len(content.splitlines()) > 25:
            preview += f"\n... ({len(content.splitlines()) - 25} more lines)"

        syntax = Syntax(preview, ext, theme="monokai", line_numbers=True)
        console.print(
            Panel(
                syntax,
                title=f"[bold yellow]Write File:[/bold yellow] [white]{filepath}[/white]",
                border_style="yellow",
                padding=(0, 1),
            )
        )
    elif tool_name == "read_file":
        console.print(f"[dim]● Read[/dim] [cyan]{args.get('filepath', '')}[/cyan]")
    elif tool_name == "list_files":
        console.print(f"[dim]● Listed[/dim] [cyan]{args.get('directory', '.')}[/cyan]")
    elif tool_name == "execute_bash":
        console.print(f"[yellow]● Ran[/yellow] [dim]({args.get('command', '')})[/dim]")
    elif tool_name in {"delegate_research", "delegate_review"}:
        is_research = tool_name == "delegate_research"
        accent = COLOR_ACCENT if is_research else "blue"
        title = (
            "Subagent: Codebase Explorer"
            if is_research
            else "Subagent: Code Reviewer"
        )
        with Live(
            Spinner("dots", text=f"[bold {accent}]Starting subagent...[/bold {accent}]"),
            console=console,
            transient=True,
            refresh_per_second=12,
        ):
            time.sleep(0.35)
        console.print(f"[{accent}]○ Thought[/{accent}] [dim]({title}: {args.get('task', '')})[/dim]")
    else:
        console.print(f"[yellow]● Ran[/yellow] [dim]({tool_name}: {args})[/dim]")


def render_tool_result(output: str, is_error: bool = False) -> None:
    """Render concise, bounded tool output."""
    lines = output.strip().splitlines()
    if not lines:
        return
    preview = "\n".join(lines[:15])
    if len(lines) > 15:
        preview += f"\n[dim]... ({len(lines) - 15} more lines hidden)[/dim]"

    style = COLOR_ERROR if is_error or output.startswith("Error") else "dim"
    console.print(f"  [{style}]{preview}[/{style}]")


def render_assistant_message(content: str) -> None:
    """Render final LLM response as formatted Markdown."""
    if not content.strip():
        return
    console.print(Markdown(content))


def render_user_message(content: str) -> None:
    """Render the submitted user prompt as a compact CLI transcript line."""
    if not content.strip():
        return
    console.print(f"[bold {COLOR_ACCENT}]>[/bold {COLOR_ACCENT}] {content}")


def print_agent_message(text: str) -> None:
    """Compatibility name for callers rendering assistant responses."""
    render_assistant_message(text)


def render_error(message: str) -> None:
    """Render graceful API/runtime errors without raw tracebacks."""
    console.print(
        Panel(
            Text(message, style="bold red"),
            title=f"[bold {COLOR_ERROR}]Error[/bold {COLOR_ERROR}]",
            border_style=COLOR_ERROR,
            padding=(0, 1),
        )
    )


def render_diff_preview(filepath: str, old_text: str, new_text: str) -> None:
    """Render colored unified diffs (ready for surgical edit_file support)."""
    diff = "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
        )
    )
    if diff:
        console.print(
            Panel(
                Syntax(diff, "diff", theme="monokai"),
                title=f"[bold green]± Diff:[/bold green] [white]{filepath}[/white]",
                border_style="green",
                padding=(0, 1),
            )
        )