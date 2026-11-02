"""Tool-calling agent loop on top of Ollama.

Intentionally framework-free: one loop that sends the conversation + tool schemas to
the model, executes any requested tools, feeds the results back and repeats until the
model answers in plain text.
"""

import json
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import ollama
from dotenv import load_dotenv

from emporio.prompts import build_system_prompt
from emporio.tools import TOOL_SCHEMAS, call_tool

load_dotenv()

SESSIONS_DIR = Path(__file__).resolve().parents[2] / "sessions"
DEFAULT_MODEL = "qwen3:14b"
MAX_TOOL_ROUNDS = 6
FALLBACK_REPLY = (
    "Desculpe, tive um probleminha para consultar o sistema agora. "
    "Você pode tentar de novo ou falar com a equipe pelo WhatsApp (67) 3321-4500?"
)

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: dict


@dataclass
class Reply:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


def _clean(text: str) -> str:
    # Reasoning models (e.g. qwen3) may emit <think> blocks; customers must not see them.
    return _THINK_BLOCK.sub("", text or "").strip()


class Agent:
    def __init__(self, model: str | None = None, session_id: str | None = None, host: str | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self.client = ollama.Client(host=host or os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        self.session_id = session_id or uuid.uuid4().hex[:8]
        # History holds user/assistant/tool messages; the system prompt is rebuilt every
        # turn so the current date/time is always fresh.
        self.history: list[dict] = self._load_session()

    # -------------------------------------------------------------- persistence

    @property
    def _session_path(self) -> Path:
        return SESSIONS_DIR / f"{self.session_id}.json"

    def _load_session(self) -> list[dict]:
        if self._session_path.exists():
            return json.loads(self._session_path.read_text(encoding="utf-8"))
        return []

    def _save_session(self) -> None:
        SESSIONS_DIR.mkdir(exist_ok=True)
        self._session_path.write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")

    def reset(self) -> None:
        self.history = []
        self._session_path.unlink(missing_ok=True)

    # --------------------------------------------------------------------- loop

    def chat(self, user_message: str) -> Reply:
        self.history.append({"role": "user", "content": user_message})
        calls: list[ToolCall] = []

        for _ in range(MAX_TOOL_ROUNDS):
            messages = [{"role": "system", "content": build_system_prompt()}, *self.history]
            try:
                response = self.client.chat(
                    model=self.model, messages=messages, tools=TOOL_SCHEMAS, options={"temperature": 0.2}
                )
            except Exception:  # connection errors, model not pulled, etc.
                self.history.pop()
                return Reply(FALLBACK_REPLY, calls)

            message = response.message
            if not message.tool_calls:
                text = _clean(message.content) or FALLBACK_REPLY
                self.history.append({"role": "assistant", "content": text})
                self._save_session()
                return Reply(text, calls)

            self.history.append({
                "role": "assistant",
                "content": _clean(message.content),
                "tool_calls": [
                    {"function": {"name": tc.function.name, "arguments": dict(tc.function.arguments)}}
                    for tc in message.tool_calls
                ],
            })
            for tc in message.tool_calls:
                args = dict(tc.function.arguments or {})
                result = call_tool(tc.function.name, args)
                calls.append(ToolCall(tc.function.name, args, result))
                self.history.append({
                    "role": "tool",
                    "name": tc.function.name,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

        self.history.append({"role": "assistant", "content": FALLBACK_REPLY})
        self._save_session()
        return Reply(FALLBACK_REPLY, calls)
