from prometheus_client import CollectorRegistry

from app.core.metrics import make_metrics


def test_make_metrics_returns_all_counters():
    registry = CollectorRegistry()
    m = make_metrics(registry=registry)
    assert m.http_requests_total is not None
    assert m.http_request_duration_seconds is not None
    assert m.http_errors_total is not None
    assert m.ai_model_requests_total is not None
    assert m.ai_model_request_duration_seconds is not None
    assert m.ai_model_errors_total is not None


def test_make_metrics_isolated_registry():
    r1 = CollectorRegistry()
    r2 = CollectorRegistry()
    m1 = make_metrics(registry=r1)
    m2 = make_metrics(registry=r2)
    assert m1 is not m2


def test_record_ai_request():
    registry = CollectorRegistry()
    m = make_metrics(registry=registry)
    m.record_ai_request("ollama", "qwen3:8b")
    val = m.ai_model_requests_total.labels(provider="ollama", model="qwen3:8b")._value.get()
    assert val == 1.0


def test_record_ai_error():
    registry = CollectorRegistry()
    m = make_metrics(registry=registry)
    m.record_ai_error("ollama", "qwen3:8b")
    val = m.ai_model_errors_total.labels(provider="ollama", model="qwen3:8b")._value.get()
    assert val == 1.0
