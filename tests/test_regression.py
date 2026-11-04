from signalforge.models import Trace
from signalforge.regression import compare


def trace(trace_id, output, latency_ms=200):
    return Trace.from_dict({
        "trace_id": trace_id,
        "input": "Question",
        "output": output,
        "latency_ms": latency_ms,
        "expected": "A useful answer.",
    })


def test_compare_detects_quality_and_risk_regression():
    result = compare(
        [trace("same", "A useful answer.")],
        [trace("same", "I cannot help.", latency_ms=4000)],
    )
    assert result["regression_count"] == 1
    regression = result["regressions"][0]
    assert regression["severity"] == "critical"
    assert "risk:" in regression["reasons"][0]
    assert result["pass"] is False


def test_compare_surfaces_dataset_drift_and_threshold():
    result = compare([trace("removed", "A useful answer.")], [trace("added", "A useful answer.")])
    assert result["added"] == ["added"]
    assert result["removed"] == ["removed"]
    assert result["shared_total"] == 0
    assert result["pass"] is False


def test_compare_rejects_bad_threshold():
    try:
        compare([], [], threshold=2)
    except ValueError as error:
        assert "threshold" in str(error)
    else:
        raise AssertionError("Expected invalid threshold to fail")
