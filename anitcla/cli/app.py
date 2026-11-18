import time
import uuid
import typer
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from anticla.cli.ui import (
    console,
    get_user_input,
    render_assistant_message,
    render_banner,
    render_error,
    render_help,
    render_tool_call,
    render_tool_result,
)
from anticla.core.config import WORKSPACE_PATH, settings

cli_app = typer.Typer(
    name="anticla",
    help="Anticla — Autonomous Agentic Coding CLI",
    no_args_is_help=True,
)


def _run_agent_turn(prompt: str, thread_id: str) -> None:
    """Stream a single agent turn with live spinner, tool cards, and Markdown output."""
    from anticla.agent.graph import ide_app

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 25,
    }
    inputs = {"messages": [HumanMessage(content=prompt)]}
    status = console.status("[bold cyan]Thinking...[/bold cyan]", spinner="dots")

    try:
        status.start()
        for event in ide_app.stream(inputs, config=config, stream_mode="updates"):
            for node_name, state_update in event.items():
                messages = state_update.get("messages", [])
                for msg in messages:
                    if isinstance(msg, AIMessage):
                        if msg.tool_calls:
                            status.stop()
                            for tc in msg.tool_calls:
                                render_tool_call(tc["name"], tc["args"])
                            status.update("[bold yellow]Running tool...[/bold yellow]")
                            status.start()
                        elif msg.content:
                            status.stop()
                            render_assistant_message(str(msg.content))
                    elif isinstance(msg, ToolMessage):
                        status.stop()
                        render_tool_result(str(msg.content))
                        status.update("[bold cyan]Thinking...[/bold cyan]")
                        status.start()
    except KeyboardInterrupt:
        status.stop()
        console.print("\n[yellow]Generation aborted (Ctrl+C). Returning to prompt...[/yellow]")
    except Exception as exc:
        status.stop()
        render_error(f"{type(exc).__name__}: {exc}")
    finally:
        status.stop()


@cli_app.command()
def run(
    prompt: str = typer.Argument(..., help="Coding instruction to execute."),
):
    """Execute a single coding task and exit."""
    active_model = (
        settings.ollama_model_id
        if settings.llm_provider == "local"
        else settings.nvidia_model_id
    )
    render_banner(settings.llm_provider, active_model, WORKSPACE_PATH)
    _run_agent_turn(prompt, thread_id=f"run_{uuid.uuid4().hex[:8]}")


@cli_app.command()
def chat():
    """Start an interactive coding session (REPL)."""
    from anticla.agent.nodes import set_active_llm

    current_provider = settings.llm_provider
    current_model = (
        settings.ollama_model_id
        if current_provider == "local"
        else settings.nvidia_model_id
    )
    thread_id = f"chat_{uuid.uuid4().hex[:8]}"
    last_interrupt_time = 0.0

    render_banner(current_provider, current_model, WORKSPACE_PATH)

    while True:
        try:
            user_input = get_user_input()
            last_interrupt_time = 0.0  # Reset double Ctrl+C timer on valid input
        except EOFError:
            console.print("\n[dim]Session ended.[/dim]")
            break
        except KeyboardInterrupt:
            now = time.monotonic()
            if now - last_interrupt_time < 2.0:
                console.print("\n[dim]Session ended.[/dim]")
                break
            last_interrupt_time = now
            console.print("\n[dim]Press Ctrl+C again within 2s (or type exit) to quit.[/dim]")
            continue

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "/exit", "/quit"}:
            console.print("[dim]Session ended.[/dim]")
            break

        # Slash commands
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "/help":
                render_help()
            elif cmd == "/clear":
                thread_id = f"chat_{uuid.uuid4().hex[:8]}"
                console.clear()
                render_banner(current_provider, current_model, WORKSPACE_PATH)
                console.print("[green]Conversation memory cleared.[/green]")
            elif cmd == "/model" and arg:
                try:
                    set_active_llm(current_provider, arg)
                    current_model = arg
                    console.print(f"[green]Switched model to[/green] [bold]{current_model}[/bold]")
                except Exception as exc:
                    render_error(f"Failed to switch model: {exc}")
            elif cmd == "/provider" and arg in {"nvidia", "local"}:
                try:
                    default_model = (
                        settings.ollama_model_id
                        if arg == "local"
                        else settings.nvidia_model_id
                    )
                    set_active_llm(arg, default_model)
                    current_provider = arg
                    current_model = default_model
                    console.print(
                        f"[green]Switched provider to[/green] [bold]{current_provider}[/bold] ({current_model})"
                    )
                except Exception as exc:
                    render_error(f"Failed to switch provider: {exc}")
            else:
                console.print("[yellow]Unknown command. Type /help to see valid commands.[/yellow]")
            continue

        _run_agent_turn(user_input, thread_id=thread_id)