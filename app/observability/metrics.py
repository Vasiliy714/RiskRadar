from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

LLM_REQUESTS_TOTAL = Counter(
    "llm_requests_total",
    "Total LLM chat requests",
    labelnames=["provider", "model", "outcome"],
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "llm_request_duration_seconds",
    "LLM chat request latency in seconds",
    labelnames=["provider", "model"],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 45, 60, 90, 120),
)

LLM_TOKENS_TOTAL = Counter(
    "llm_tokens_total",
    "Total LLM tokens",
    labelnames=["provider", "model", "direction"],
)
