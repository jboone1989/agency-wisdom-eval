from __future__ import annotations

import json
import subprocess
import threading
from typing import Sequence

from ..models import AgentDecision, Scenario


class ContestantExecutionError(RuntimeError):
    """Contestant-side infrastructure/provider failure, distinct from a scored choice."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code or "contestant_error")
        self.detail = str(detail or "")
        super().__init__(
            self.code + (": " + self.detail if self.detail else "")
        )


class JsonLineSubprocessAgent:
    """Language-neutral contestant adapter over newline-delimited JSON.

    The contestant is a long-lived process so its own memory can persist across
    E2/E3 episodes. Evaluator-private scoring data is never transmitted.
    """

    def __init__(self, command: Sequence[str], *, name: str, timeout_seconds: float = 30.0) -> None:
        if not command:
            raise ValueError("contestant command is required")
        self.name = str(name)
        self.timeout_seconds = float(timeout_seconds)
        self._process = subprocess.Popen(
            list(command),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self._lock = threading.Lock()

    def _roundtrip(self, payload: dict) -> dict:
        if self._process.poll() is not None:
            raise ContestantExecutionError(
                "process_exited", f"code={self._process.returncode}"
            )
        if self._process.stdin is None or self._process.stdout is None:
            raise ContestantExecutionError("pipes_unavailable")
        with self._lock:
            self._process.stdin.write(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            self._process.stdin.flush()

            result: dict | None = None
            error: list[BaseException] = []

            def read_one() -> None:
                nonlocal result
                try:
                    line = self._process.stdout.readline()
                    if not line:
                        raise ContestantExecutionError("stdout_closed")
                    parsed = json.loads(line)
                    if not isinstance(parsed, dict):
                        raise ContestantExecutionError(
                            "protocol_error", "response must be a JSON object"
                        )
                    result = parsed
                except BaseException as exc:
                    error.append(exc)

            thread = threading.Thread(target=read_one, daemon=True)
            thread.start()
            thread.join(self.timeout_seconds)
            if thread.is_alive():
                self.close(kill=True)
                raise ContestantExecutionError(
                    "timeout", f"exceeded {self.timeout_seconds}s response timeout"
                )
            if error:
                exc = error[0]
                if isinstance(exc, ContestantExecutionError):
                    raise exc
                raise ContestantExecutionError("protocol_error", str(exc)) from exc
            assert result is not None
            if result.get("ok") is False:
                raise ContestantExecutionError(
                    str(result.get("error") or "contestant_error"),
                    str(result.get("detail") or "")[:1000],
                )
            return result

    def begin_scenario(self, scenario: Scenario, persistent_state: dict) -> None:
        reply = self._roundtrip({
            "type": "begin_scenario",
            "scenario": {
                "id": scenario.id,
                "title": scenario.title,
                "level": scenario.level.value,
                "tags": list(scenario.tags),
            },
        })
        if reply.get("ok") is not True:
            raise ContestantExecutionError("scenario_start_rejected")

    def decide(
        self,
        *,
        observation: str,
        actions: dict[str, str],
        public_world: dict,
        persistent_state: dict,
    ) -> AgentDecision:
        reply = self._roundtrip({
            "type": "decide",
            "observation": observation,
            "actions": actions,
            "public_world": public_world,
        })
        action_id = str(reply.get("action_id") or "")
        beliefs = reply.get("declared_beliefs")
        confidence = reply.get("declared_confidence")
        return AgentDecision(
            action_id=action_id,
            declared_beliefs=dict(beliefs) if isinstance(beliefs, dict) else {},
            declared_confidence=float(confidence) if isinstance(confidence, (int, float)) else None,
        )

    def observe_outcome(
        self,
        *,
        action_id: str,
        outcome: str,
        public_world: dict,
        persistent_state: dict,
    ) -> None:
        reply = self._roundtrip({
            "type": "outcome",
            "action_id": action_id,
            "outcome": outcome,
            "public_world": public_world,
        })
        if reply.get("ok") is not True:
            raise ContestantExecutionError("outcome_rejected")

    def close(self, *, kill: bool = False) -> None:
        if self._process.poll() is not None:
            return
        try:
            if not kill and self._process.stdin is not None:
                self._process.stdin.write('{"type":"close"}\n')
                self._process.stdin.flush()
        except OSError:
            pass
        try:
            self._process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            self._process.kill()
            self._process.wait(timeout=1)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


__all__ = ["ContestantExecutionError", "JsonLineSubprocessAgent"]
