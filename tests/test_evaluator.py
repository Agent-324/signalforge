import pytest

from signalforge.evaluator import evaluate, summarize
from signalforge.models import Trace


def make_trace(**kwargs):
    values = {"trace_id": "t-1", "input": "Question", "output": "A useful answer.", "latency_ms": 200}
    values.update(kwargs)
    return Trace.from_dict(values)


def test_evaluate_returns_explainable_findings():
    result = evaluate(make_trace(expected="A useful answer."))
    assert result.risk == "healthy"
    assert {finding.name for finding in result.findings} == {
        "Reference alignment", "Confidence", "Safety / privacy", "Helpfulness", "Latency"
    }
    assert all(finding.evidence for finding in result.findings)


def test_evaluate_flags_pii_and_slow_refusal():
    result = evaluate(make_trace(output="I cannot help. Email me at person@example.com", latency_ms=4000))
    assert result.risk == "critical"
    assert next(f for f in result.findings if f.name == "Safety / privacy").status == "fail"
    assert next(f for f in result.findings if f.name == "Latency").status == "fail"


def test_summarize_empty_and_counts():
    assert summarize([])["total"] == 0
    results = [evaluate(make_trace(trace_id="a")), evaluate(make_trace(trace_id="b", latency_ms=4000))]
    summary = summarize(results)
    assert summary["total"] == 2
    assert summary["models"] == {"unknown": 2}


def test_missing_required_fields_is_explicit():
    with pytest.raises(ValueError, match="trace_id"):
        Trace.from_dict({"input": "x", "output": "y"})
