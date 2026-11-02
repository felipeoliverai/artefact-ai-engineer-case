"""Terminal chat, mainly for development: `uv run emporio-cli --debug` shows every tool call."""

import argparse
import json

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from emporio.agent import Agent

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(description="Empório da Música — atendimento via terminal")
    parser.add_argument("--model", help="Ollama model (default: $OLLAMA_MODEL or qwen3:14b)")
    parser.add_argument("--session", help="Session id to resume a previous conversation")
    parser.add_argument("--debug", action="store_true", help="Show tool calls and results")
    args = parser.parse_args()

    agent = Agent(model=args.model, session_id=args.session)
    console.print(Panel(
        f"Empório da Música — assistente virtual\nmodelo: {agent.model} · sessão: {agent.session_id}\n"
        "Comandos: /reset limpa a conversa, /sair encerra.",
        style="cyan",
    ))

    while True:
        try:
            user = console.input("[bold green]Você:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user in ("/sair", "/exit", "/quit"):
            break
        if user == "/reset":
            agent.reset()
            console.print("[dim]Conversa reiniciada.[/]")
            continue

        with console.status("Lia está digitando..."):
            reply = agent.chat(user)
        if args.debug:
            for call in reply.tool_calls:
                console.print(Panel(
                    f"{json.dumps(call.arguments, ensure_ascii=False)}\n→ "
                    f"{json.dumps(call.result, ensure_ascii=False, default=str)[:1200]}",
                    title=f"tool: {call.name}", style="dim",
                ))
        console.print("[bold magenta]Lia:[/]", Markdown(reply.text))


if __name__ == "__main__":
    main()
