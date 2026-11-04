from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Trace:
    trace_id: str
    input: str
    output: str
    expected: str | None = None
    latency_ms: float = 0.0
    tokens: int = 0
    model: str = "unknown"
    timestamp: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Trace":
        required = ("trace_id", "input", "output")
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise ValueError(f"Trace is missing required fields: {', '.join(missing)}")
        return cls(
            trace_id=str(data["trace_id"]),
            input=str(data["input"]),
            output=str(data["output"]),
            expected=str(data["expected"]) if data.get("expected") is not None else None,
            latency_ms=float(data.get("latency_ms", 0)),
            tokens=int(data.get("tokens", 0)),
            model=str(data.get("model", "unknown")),
            timestamp=str(data.get("timestamp", utc_now())),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "input": self.input,
            "output": self.output,
            "expected": self.expected,
            "latency_ms": self.latency_ms,
            "tokens": self.tokens,
            "model": self.model,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class Finding:
    name: str
    score: float
    status: str
    explanation: str
    evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "score": round(self.score, 3),
            "status": self.status,
            "explanation": self.explanation,
            "evidence": self.evidence,
        }


@dataclass(frozen=True)
class ScoredTrace:
    trace: Trace
    score: float
    risk: str
    findings: list[Finding]

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.trace.to_dict(),
            "score": round(self.score, 3),
            "risk": self.risk,
            "findings": [finding.to_dict() for finding in self.findings],
        }

