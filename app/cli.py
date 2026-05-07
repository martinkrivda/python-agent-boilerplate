"""Command-line interface for python-agent-boilerplate.

Exposes the same agent core as the HTTP service, but for terminal usage:

    agent version             show the package version
    agent models              show the configured AI provider (no secrets)
    agent ask "..."           run the agent on a single prompt and print the answer
    agent chat                interactive REPL (Ctrl+D / 'exit' to quit)
    agent serve               start the FastAPI HTTP service

Provider configuration is read from environment variables / `.env` via the
shared `Settings` class — same as the HTTP service.
"""

from __future__ import annotations

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from app import __version__
from app.agents.schemas import AgentRunRequest
from app.ai.model_settings import ModelSettings
from app.ai.providers.openai_compatible import OpenAICompatibleModelClient
from app.core.config import Settings
from app.core.errors import AppError
from app.services.agent_service import AgentService

app = typer.Typer(
    name="agent",
    help="CLI for python-agent-boilerplate.",
    add_completion=False,
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True)


def _service(settings: Settings | None = None) -> AgentService:
    settings = settings or Settings()
    return AgentService(
        model_client=OpenAICompatibleModelClient(settings),
        model_settings=ModelSettings.from_settings(settings),
    )


def _run(coro):
    try:
        return asyncio.run(coro)
    except AppError as exc:
        err_console.print(f"[red]{exc.title} ({exc.code})[/red]: {exc.detail}")
        raise typer.Exit(2) from exc
    except KeyboardInterrupt:
        err_console.print("[yellow]interrupted[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def version() -> None:
    """Show the package version."""
    console.print(f"python-agent-boilerplate {__version__}")


@app.command()
def models() -> None:
    """Show the configured AI provider (no secrets)."""
    ms = ModelSettings.from_settings(Settings())
    console.print_json(data=ms.model_dump())


@app.command()
def ask(
    message: Annotated[str, typer.Argument(help="The question to ask.")],
    system: Annotated[
        str | None,
        typer.Option("--system", "-s", help="Override the default system prompt."),
    ] = None,
    temperature: Annotated[
        float | None,
        typer.Option("--temperature", "-t", min=0.0, max=2.0),
    ] = None,
    max_tokens: Annotated[
        int | None,
        typer.Option("--max-tokens", "-m", min=1),
    ] = None,
    plain: Annotated[
        bool,
        typer.Option("--plain", help="Print the answer without Markdown formatting."),
    ] = False,
) -> None:
    """Ask the agent a single question and print the answer."""
    service = _service()
    request = AgentRunRequest(
        message=message,
        system_prompt=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    result = _run(service.run(request))
    if plain:
        console.print(result.answer)
    else:
        console.print(Markdown(result.answer))


@app.command()
def chat() -> None:
    """Start an interactive chat REPL.

    Each turn is independent — there is no conversation memory in v1. Type
    'exit' / 'quit' or press Ctrl+D to leave.
    """
    settings = Settings()
    service = _service(settings)
    banner = (
        f"[bold]python-agent-boilerplate[/bold] {__version__}\n"
        f"model: [cyan]{settings.ai_model}[/cyan] · "
        f"provider: [cyan]{settings.ai_provider}[/cyan]\n"
        "[dim]Ctrl+D, Ctrl+C, 'exit' or 'quit' to leave. "
        "No conversation memory — each turn is independent.[/dim]"
    )
    console.print(Panel(banner, expand=False))

    while True:
        try:
            message = Prompt.ask("[bold cyan]you[/bold cyan]")
        except EOFError, KeyboardInterrupt:
            console.print()
            break
        clean = message.strip()
        if not clean:
            continue
        if clean.lower() in {"exit", "quit", "/exit", "/quit"}:
            break
        request = AgentRunRequest(message=clean)
        try:
            result = asyncio.run(service.run(request))
        except AppError as exc:
            err_console.print(f"[red]{exc.title} ({exc.code})[/red]: {exc.detail}\n")
            continue
        console.print("[bold green]agent[/bold green]")
        console.print(Markdown(result.answer))
        console.print()


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", "-h")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p")] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload", help="Enable auto-reload (development only)."),
    ] = False,
) -> None:
    """Start the FastAPI HTTP service."""
    import uvicorn

    uvicorn.run("app.main:app", host=host, port=port, reload=reload)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
