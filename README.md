# Anticla CLI

> **Autonomous, Sandboxed Agentic Software Engineering CLI & SDK** powered natively by **LangGraph**, **NVIDIA NIM**, and local **Ollama** runtimes.

[![Status: Under Development](https://img.shields.io/badge/status-under--development-orange.svg)]()
[![Orchestration: LangGraph](https://img.shields.io/badge/orchestration-LangGraph-blue.svg)](https://github.com/langchain-ai/langgraph)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)]()

> [!WARNING]
> **Under Active Development (Alpha)**: Anticla is undergoing active development. Internal graph transitions, tool bindings, CLI subcommands, and SDK signatures are subject to refinement. Ensure execution takes place inside designated sandbox directories.

---

## Executive Summary

**Anticla** is a developer-centric autonomous coding assistant designed to bridge high-throughput cloud reasoning with local private inference. Built from the ground up on **LangGraph's cyclic state graphs**, Anticla replaces fragile linear agent chains with a deterministic, state-driven workflow featuring checkpointed conversation memory, human-in-the-loop safety approvals, and isolated subagent delegation.

---

## Core Capabilities

- **Cyclic LangGraph Architecture**: Utilizes compiled `StateGraph` state machines with in-memory checkpointing (`MemorySaver`) and conditional tool loop routing.
- **Hierarchical Subagent Isolation**: Spawns stateless, ephemeral LangGraph sub-graphs for repository exploration (`delegate_research`) and quality assurance (`delegate_review`), preventing context window contamination.
- **Dual-Engine Model Flexibility**:
  - **Cloud Accelerated**: High-throughput reasoning via **NVIDIA NIM** (`ChatNVIDIA`).
  - **Local & Private**: Completely offline, sovereign inference via **Ollama** (`ChatOllama`).
- **Human-in-the-Loop Security Gate**: Destructive shell operations (`execute_bash`) intercept execution and require explicit user authorization (`[y/N]`) before execution.
- **Sandboxed Workspace**: Path-traversal protection restricts autonomous file operations to `./workspace` by default.
- **Parallel Line TUI Framing**: Custom `PromptSession` layout framing the active input bar between live top and bottom horizontal rules.
- **Embeddable Python SDK**: First-class programmatic API (`AnticlaSDK`) for embedding autonomous agent tasks into custom tools, scripts, and CI/CD pipelines.

---

## System Architecture

```
                                ┌───────────────────────────┐
                                │     User Interaction      │
                                │  `anticla chat` / `run`   │
                                └─────────────┬─────────────┘
                                              │
                                              ▼
                                ┌───────────────────────────┐
                                │    Parallel Divider TUI   │
                                │   (prompt_toolkit + Rich) │
                                └─────────────┬─────────────┘
                                              │
                                              ▼
                                ┌───────────────────────────┐
                                │   Main StateGraph Agent   │
                                │    `IDEState` Checkpoint  │
                                └──────┬─────────────┬──────┘
                                       │             │
                ┌──────────────────────┘             └──────────────────────┐
                ▼                                                           ▼
  ┌───────────────────────────┐                               ┌───────────────────────────┐
  │ Subgraph: Explorer        │                               │ Subgraph: Reviewer        │
  │ Isolated Research Agent   │                               │ Verification & QA Agent   │
  │ Tools: [list_files, read] │                               │ Tools: [list, read, bash] │
  └─────────────┬─────────────┘                               └─────────────┬─────────────┘
                │                                                           │
                └──────────────────────┬────────────────────────────────────┘
                                       ▼
                        ┌───────────────────────────┐
                        │    Workspace Tool Layer   │
                        │ - `read_file`             │
                        │ - `write_file` (diff cards│
                        │ - `execute_bash` ([y/N])  │
                        └───────────────────────────┘
```

---

## LangGraph Multi-Agent Engine

Anticla avoids traditional rigid agent loops by implementing **LangGraph's state graph paradigm**. The execution lifecycle divides cleanly between parent coordination and ephemeral subagent execution.

### 1. Primary Agent StateGraph (`IDEState`)

The root agent runs as a compiled cyclic `StateGraph(IDEState)` equipped with an in-memory checkpointer (`MemorySaver`):

- **State Model**:
  ```python
  class IDEState(TypedDict):
      messages: Annotated[Sequence[BaseMessage], add_messages]
  ```
- **Execution Topology**:
  - `START ──► coder ──► route_after_agent`
  - If tool calls are detected: `route_after_agent ──► tools ──► coder` (cyclic loop).
  - If no tool calls are detected: `route_after_agent ──► END`.
- **Dynamic Tool Execution**: The `ToolNode(ide_tools)` dispatches file operations and subagent invocations, looping back to the reasoning node until the task reaches verified completion.

### 2. Ephemeral Subagent Subgraphs

To prevent conversation context degradation when surveying large repositories, Anticla dynamically compiles and runs lightweight, bounded subgraphs on demand:

```python
def _run_isolated_subagent(system_prompt, task, tools, recursion_limit=12) -> str:
    # Compiles a dedicated StateGraph(MessagesState) with scoped tools
    builder = StateGraph(MessagesState)
    builder.add_node("worker", subagent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "worker")
    builder.add_conditional_edges("worker", tools_condition)
    builder.add_edge("tools", "worker")
    sub_graph = builder.compile()
    ...
```

- **Explorer Agent (`delegate_research`)**: Scoped strictly to read-only utilities (`list_files`, `read_file`). Traverses directory structures and symbol references, returning a consolidated synthesis to the parent graph.
- **Reviewer Agent (`delegate_review`)**: Dedicated QA auditor with access to read operations and test command verification. Audits syntax, structural integrity, and regressions before final delivery.
- **Recursion Ceiling**: Enforces an explicit recursion barrier (`recursion_limit=12`) to prevent unbounded tool loops.

---

## Terminal User Interface (TUI)

Anticla's interactive console provides a developer-first terminal experience:

- **Parallel Input Bar**: The active prompt is cleanly enclosed between live, simultaneous top and bottom horizontal rules rendered via a custom `ParallelPromptSession` layout:
  ```text
  ──────────────────────────────────────────────────────────────────────────────
  > Build a FastAPI service with SQLite database support
  ──────────────────────────────────────────────────────────────────────────────
  ```
- **Syntax-Highlighted Tool Cards**: File write operations and command diffs render with dedicated syntax highlighting, byte size indicators, and status badges.
- **Live Status Spinners**: High-visibility spinners indicate active model inference and background subagent analysis.

---

## Security & Governance Gates

Anticla implements strict boundary isolation across all execution pathways:

1. **Human-in-the-Loop Bash Gate**: Shell commands (`execute_bash`) are never executed blindly. The CLI displays the proposed command in an explicit confirmation card and halts execution until the operator enters `y` or `N`.
2. **Path Traversal Sandboxing**: All file read and write operations resolve against the configured workspace directory (`./workspace`). Attempts to break out of the workspace boundary raise path validation exceptions.
3. **Zero Hardcoded Secrets**: All authentication keys and endpoint URLs are externalized via environment variables and validated through Pydantic BaseSettings.
4. **Credential Isolation**: Configured `.gitignore` barriers prevent accidental staging of environment files, keys, and session artifacts.

---

## Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **Git**
- *(Optional)* **Ollama**: Installed and running locally for offline inference

### Setup & Installation

```powershell
# 1. Clone the repository
git clone https://github.com/<your-username>/anticla.git
cd anticla

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install dependencies in editable mode
pip install -e .
```

---

## Configuration

Configure your environment variables in a `.env` file at the root of the project:

```env
# Runtime Provider: "nvidia" (cloud) or "local" (Ollama)
LLM_PROVIDER=nvidia

# NVIDIA NIM Configuration (https://build.nvidia.com)
NVIDIA_API_KEY=nvapi-your-api-key-here
NVIDIA_MODEL_ID=nvidia/nemotron-3.5-bolt-e4b

# Local Ollama Configuration (when LLM_PROVIDER=local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_ID=qwen2.5-coder:7b

# Sandboxed Workspace Directory
WORKSPACE_DIR=./workspace
```

---

## Workflows & Usage

### 1. Interactive Coding REPL (`anticla chat`)

Launch the stateful, multi-turn coding environment:

```powershell
anticla chat
```

#### In-Session Slash Commands

| Slash Command | Parameter | Function |
| :--- | :--- | :--- |
| `/help` | — | Display the interactive command reference |
| `/provider` | `<nvidia\|local>` | Hot-swap LLM backend between NVIDIA NIM and Ollama |
| `/model` | `<model_id>` | Switch the active model checkpoint in the active session |
| `/clear` | — | Reset conversation memory and start a fresh state graph |
| `exit` / `quit` | — | Terminate the interactive session cleanly |

> **Interrupt Handling**: Press `Ctrl+C` to cancel in-flight streaming. Press `Ctrl+C` twice within two seconds to exit immediately.

---

### 2. Headless Task Execution (`anticla run`)

Run a discrete, single-turn software engineering task and return immediately to the terminal:

```powershell
anticla run "Scaffold a Python package with pyproject.toml, pytest configuration, and GitHub Actions CI"
```

---

### 3. Programmatic Python SDK (`AnticlaSDK`)

Embed Anticla directly into custom workflows, automation daemons, or testing pipelines:

```python
from anticla.sdk import AnticlaSDK

# Initialize the client
sdk = AnticlaSDK(
    workspace="./my_project",
    provider="nvidia",
    model="nvidia/nemotron-3.5-bolt-e4b"
)

# Dispatch an autonomous coding task
result = sdk.run_task(
    "Implement a rate-limiter decorator using redis and add unit test coverage"
)

print(result)
```

---

## Project Structure

```
anticla/
├── anticla/
│   ├── agent/                 # LangGraph state machine & subagent workflows
│   │   ├── subagent/          # Isolated Explorer & Reviewer sub-graphs
│   │   │   ├── subagents.py   # Subagent runners & tool definitions
│   │   │   └── system_prompt.py
│   │   ├── graph.py           # Main StateGraph(IDEState) compiled workflow
│   │   ├── nodes.py           # Model bindings & ToolNode executor
│   │   ├── state.py           # IDEState schema with add_messages
│   │   └── system_prompt.py   # Root orchestration prompt & guidelines
│   ├── cli/                   # Developer Terminal Interface
│   │   ├── app.py             # Typer CLI application (`chat`, `run`)
│   │   └── ui.py              # Parallel divider session & Rich renderers
│   ├── core/                  # Core configuration & settings
│   │   └── config.py          # Pydantic BaseSettings environment schema
│   ├── tools/                 # Sandboxed tool implementations
│   │   ├── file_ops.py        # Sandboxed read_file, write_file, list_files
│   │   └── terminal.py        # Human-in-the-loop execute_bash
│   ├── sdk.py                 # Embeddable AnticlaSDK wrapper
│   └── __main__.py            # Module entrypoint (`python -m anticla`)
├── pyproject.toml             # Packaging, entry points & dependencies
├── requirements.txt           # Frozen environment requirements
└── .gitignore                 # Enterprise secret & artifact exclusions
```

---

## Roadmap

- [x] Cyclic LangGraph state graph with in-memory checkpointer
- [x] Dual-engine support: NVIDIA NIM Cloud + Local Ollama
- [x] Isolated Explorer & Reviewer hierarchical subgraphs
- [x] Human-in-the-loop bash confirmation gate (`[y/N]`)
- [x] Parallel divider prompt input bar
- [x] Embeddable Python SDK (`AnticlaSDK`)
- [ ] Token-by-token streaming visualization for tool outputs
- [ ] Multi-turn workspace file diff rollbacks and checkpoint restore
- [ ] Persistent SQLite chat session history across restarts

---

## License

This project is licensed under the [MIT License](LICENSE).
