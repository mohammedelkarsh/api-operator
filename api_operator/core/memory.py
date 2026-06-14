from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class Message:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Session:
    id: str
    adapter: str
    messages: list[Message] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    pending_confirmation: dict[str, Any] | None = None

    def add(self, role: str, content: str, **metadata: Any) -> None:
        self.messages.append(Message(role=role, content=content, metadata=metadata))

    def history(self, limit: int = 20) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages[-limit:]]


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, adapter: str, session_id: str | None = None) -> Session:
        sid = session_id or str(uuid4())
        session = Session(id=sid, adapter=adapter)
        self._sessions[sid] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None, adapter: str) -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create(adapter=adapter, session_id=session_id)
