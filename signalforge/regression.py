from __future__ import annotations

from dataclasses import dataclass

from .evaluator import evaluate
from .models import ScoredTrace, Trace

_RISK_RANK = {"healthy": 0, "elevated": 1, "critical": 2}


@dataclass(frozen=True)
class Regression:
    trace_id: str
    baseline_score: float
    candidate_score: float
    delta: float
    baseline_risk: str
    candidate_risk: str
    severity: str
    reasons: list[str]

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "baseline_score": round(self.baseline_score, 3),
            "candidate_score": round(self.candidate_score, 3),
            "delta": round(self.delta, 3),
            "baseline_risk": self.baseline_risk,
            "candidate_risk": self.candidate_risk,
            "severity": self.severity,
            "reasons": self.reasons,
        }


def _finding_changes(baseline: ScoredTrace, candidate: ScoredTrace) -> list[str]:
    old = {finding.name: finding for finding in baseline.findings}
    changes = []
    for finding in candidate.findings:
        previous = old.get(finding.name)
        if previous and finding.score < previous.score - 0.05:
            changes.append(f"{finding.name}: {previous.score:.0%} -> {finding.score:.0%}")
    return changes


def compare(
    baseline: list[Trace],
    candidate: list[Trace],
    threshold: float = 0.1,
) -> dict:
    """Compare two versions of the same evaluation set.

    A regression is emitted when quality drops beyond ``threshold`` or risk
    worsens. Missing IDs are reported separately so dataset drift is visible.
    """
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    baseline_results = {trace.trace_id: evaluate(trace) for trace in baseline}
    candidate_results = {trace.trace_id: evaluate(trace) for trace in candidate}
    shared_ids = sorted(baseline_results.keys() & candidate_results.keys())
    regressions: list[Regression] = []
    for trace_id in shared_ids:
        old, new = baseline_results[trace_id], candidate_results[trace_id]
        delta = new.score - old.score
        risk_worsened = _RISK_RANK[new.risk] > _RISK_RANK[old.risk]
        if delta < -threshold or risk_worsened:
            reasons = _finding_changes(old, new)
            if risk_worsened:
                reasons.insert(0, f"risk: {old.risk} -> {new.risk}")
            severity = (
                "critical"
                if new.risk == "critical" or delta <= -0.25
                else "high"
                if risk_worsened or delta <= -0.15
                else "medium"
            )
            regressions.append(
                Regression(
                    trace_id=trace_id,
                    baseline_score=old.score,
                    candidate_score=new.score,
                    delta=delta,
                    baseline_risk=old.risk,
                    candidate_risk=new.risk,
                    severity=severity,
                    reasons=reasons or [f"score delta: {delta:.0%}"],
                )
            )
    regressions.sort(key=lambda item: ({"critical": 0, "high": 1, "medium": 2}[item.severity], item.delta))
    return {
        "baseline_total": len(baseline),
        "candidate_total": len(candidate),
        "shared_total": len(shared_ids),
        "added": sorted(candidate_results.keys() - baseline_results.keys()),
        "removed": sorted(baseline_results.keys() - candidate_results.keys()),
        "regressions": [item.to_dict() for item in regressions],
        "regression_count": len(regressions),
        "pass": not regressions and not (baseline_results.keys() - candidate_results.keys()),
    }
