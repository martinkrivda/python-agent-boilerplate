from dataclasses import dataclass
from prometheus_client import CollectorRegistry, Counter, Histogram, REGISTRY


@dataclass
class Metrics:
    http_requests_total: Counter
    http_request_duration_seconds: Histogram
    http_errors_total: Counter
    ai_model_requests_total: Counter
    ai_model_request_duration_seconds: Histogram
    ai_model_errors_total: Counter

    def record_ai_request(self, provider: str, model: str) -> None:
        self.ai_model_requests_total.labels(provider=provider, model=model).inc()

    def record_ai_error(self, provider: str, model: str) -> None:
        self.ai_model_errors_total.labels(provider=provider, model=model).inc()

    def observe_ai_duration(self, provider: str, model: str, seconds: float) -> None:
        self.ai_model_request_duration_seconds.labels(provider=provider, model=model).observe(seconds)


def make_metrics(registry: CollectorRegistry | None = None) -> Metrics:
    reg = registry or REGISTRY
    return Metrics(
        http_requests_total=Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "route", "status_code"],
            registry=reg,
        ),
        http_request_duration_seconds=Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "route"],
            registry=reg,
        ),
        http_errors_total=Counter(
            "http_errors_total",
            "Total HTTP errors",
            ["status_code", "error_code"],
            registry=reg,
        ),
        ai_model_requests_total=Counter(
            "ai_model_requests_total",
            "Total AI model requests",
            ["provider", "model"],
            registry=reg,
        ),
        ai_model_request_duration_seconds=Histogram(
            "ai_model_request_duration_seconds",
            "AI model request duration",
            ["provider", "model"],
            registry=reg,
        ),
        ai_model_errors_total=Counter(
            "ai_model_errors_total",
            "Total AI model errors",
            ["provider", "model"],
            registry=reg,
        ),
    )


_default_metrics: Metrics | None = None


def get_metrics() -> Metrics:
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = make_metrics()
    return _default_metrics
