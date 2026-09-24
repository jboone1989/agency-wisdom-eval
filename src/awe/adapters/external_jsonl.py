from __future__ import annotations

import json
import selectors
import subprocess
from typing import Any, Mapping, Sequence


class ExternalContestantError(RuntimeError):
    pass


class ExternalContestantClient:
    """Synchronous JSONL client for an isolated external benchmark contestant."""

    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 90.0) -> None:
        if not command:
            raise ValueError("contestant command is required")
        self.command = [str(x) for x in command]
        self.timeout_seconds = float(timeout_seconds)
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def _request(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if self.process.poll() is not None:
            detail = ""
            if self.process.stderr is not None:
                detail = self.process.stderr.read()[-2000:]
            raise ExternalContestantError(
                f"contestant process exited: {self.process.returncode}: {detail}"
            )
        if self.process.stdin is None or self.process.stdout is None:
            raise ExternalContestantError("contestant pipes unavailable")
        self.process.stdin.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")
        self.process.stdin.flush()

        selector = selectors.DefaultSelector()
        try:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            ready = selector.select(self.timeout_seconds)
        finally:
            selector.close()
        if not ready:
            self.process.kill()
            self.process.wait(timeout=3)
            detail = ""
            if self.process.stderr is not None:
                detail = self.process.stderr.read()[-2000:]
            raise ExternalContestantError(
                f"contestant timed out after {self.timeout_seconds:.1f}s: {detail}"
            )

        line = self.process.stdout.readline()
        if not line:
            raise ExternalContestantError("contestant produced no response")
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ExternalContestantError(f"invalid contestant JSON: {line[:500]!r}") from exc
        if not isinstance(response, dict):
            raise ExternalContestantError("contestant response must be an object")
        if response.get("ok") is False:
            raise ExternalContestantError(
                f"{response.get('error')}: {response.get('detail')}"
            )
        return response

    def begin_episode(
        self,
        *,
        benchmark_id: str,
        episode_id: str,
        title: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request({
            "type": "begin_episode",
            "benchmark_id": benchmark_id,
            "episode_id": episode_id,
            "title": title,
            "metadata": dict(metadata or {}),
        })

    def choose(
        self,
        *,
        observation: str,
        actions: Mapping[str, str],
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request({
            "type": "choose",
            "observation": observation,
            "actions": dict(actions),
            "context": dict(context or {}),
        })

    def respond(
        self,
        *,
        observation: str,
        instruction: str = "",
        context: Mapping[str, Any] | None = None,
        max_chars: int = 8000,
    ) -> dict[str, Any]:
        return self._request({
            "type": "respond",
            "observation": observation,
            "instruction": instruction,
            "context": dict(context or {}),
            "max_chars": int(max_chars),
        })

    def tool_turn(
        self,
        *,
        observation: str,
        instruction: str,
        tools: Sequence[Mapping[str, Any]],
        context: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request({
            "type": "tool_turn",
            "observation": observation,
            "instruction": instruction,
            "tools": [dict(tool) for tool in tools],
            "context": dict(context or {}),
        })

    def outcome(
        self,
        *,
        action: str,
        outcome: str,
        public_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request({
            "type": "outcome",
            "action": action,
            "outcome": outcome,
            "public_state": dict(public_state or {}),
        })

    def close(self) -> None:
        if self.process.poll() is not None:
            return
        if self.process.stdin is not None:
            try:
                self.process.stdin.write('{"type":"close"}\n')
                self.process.stdin.flush()
            except BrokenPipeError:
                pass
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=3)

    def __enter__(self) -> "ExternalContestantClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
