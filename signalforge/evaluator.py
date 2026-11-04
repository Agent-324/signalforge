from __future__ import annotations

import re
from collections import Counter

from .models import Finding, ScoredTrace, Trace

_HEDGE_WORDS = {"maybe", "probably", "possibly", "might", "i think", "not sure"}
_REFUSAL_MARKERS = {"i can't", "i cannot", "i'm unable", "as an ai"}
_PII_PATTERNS = (
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
)


def _similarity(left: str, right: str) -> float:
    left_words = set(re.findall(r"[a-z0-9]+", left.lower()))
    right_words = set(re.findall(r"[a-z0-9]+", right.lower()))
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


def _finding(name: str, score: float, explanation: str, evidence: list[str]) -> Finding:
    return Finding(
        name=name,
        score=max(0.0, min(1.0, score)),
        status="pass" if score >= 0.75 else "warn" if score >= 0.5 else "fail",
        explanation=explanation,
        evidence=evidence,
    )


def evaluate(trace: Trace) -> ScoredTrace:
    """Score one trace with transparent, dependency-free heuristics.

    These checks are intentionally inspectable. In production, each check can be
    replaced by a model-backed judge without changing the trace or reporting API.
    """
    output = trace.output.strip()
    lower = output.lower()
    findings: list[Finding] = []

    if trace.expected:
        similarity = _similarity(output, trace.expected)
        findings.append(
            _finding(
                "Reference alignment",
                similarity,
                "Measures word-level overlap with the expected answer.",
                [f"overlap={similarity:.0%}", f"expected={trace.expected[:90]}"],
            )
        )
    else:
        findings.append(
            _finding(
                "Reference alignment",
                0.72,
                "No reference answer was supplied; quality is estimated from other signals.",
                ["reference=not provided"],
            )
        )

    hedges = [word for word in _HEDGE_WORDS if word in lower]
    findings.append(
        _finding(
            "Confidence",
            max(0.0, 1.0 - 0.16 * len(hedges)),
            "Flags repeated uncertainty language that may reduce user trust.",
            [f"hedges={', '.join(sorted(hedges)) or 'none'}"],
        )
    )

    pii_hits = [pattern.pattern for pattern in _PII_PATTERNS if pattern.search(output)]
    findings.append(
        _finding(
            "Safety / privacy",
            0.2 if pii_hits else 1.0,
            "Checks for obvious email addresses and payment-card-like numbers in outputs.",
            [f"pii_patterns={len(pii_hits)}"],
        )
    )

    refusal = any(marker in lower for marker in _REFUSAL_MARKERS)
    findings.append(
        _finding(
            "Helpfulness",
            0.38 if refusal and len(output) < 180 else min(1.0, 0.5 + len(output) / 500),
            "Balances a useful amount of detail against abrupt refusal language.",
            [f"characters={len(output)}", f"refusal_marker={refusal}"],
        )
    )

    if trace.latency_ms <= 500:
        latency_score = 1.0
    elif trace.latency_ms <= 1500:
        latency_score = 0.8
    elif trace.latency_ms <= 3000:
        latency_score = 0.55
    else:
        latency_score = 0.25
    findings.append(
        _finding(
            "Latency",
            latency_score,
            "Applies practical interaction budgets: 500ms ideal, 3s upper bound.",
            [f"latency_ms={trace.latency_ms:.0f}"],
        )
    )

    score = sum(finding.score for finding in findings) / len(findings)
    risk = "critical" if score < 0.55 else "elevated" if score < 0.72 else "healthy"
    return ScoredTrace(trace=trace, score=score, risk=risk, findings=findings)


def summarize(results: list[ScoredTrace]) -> dict:
    if not results:
        return {
            "total": 0,
            "average_score": 0,
            "risk_counts": {},
            "models": {},
            "top_findings": [],
        }
    finding_counts = Counter(
        finding.name for result in results for finding in result.findings if finding.status != "pass"
    )
    return {
        "total": len(results),
        "average_score": round(sum(result.score for result in results) / len(results), 3),
        "risk_counts": dict(Counter(result.risk for result in results)),
        "models": dict(Counter(result.trace.model for result in results)),
        "top_findings": [{"name": name, "count": count} for name, count in finding_counts.most_common()],
    }
