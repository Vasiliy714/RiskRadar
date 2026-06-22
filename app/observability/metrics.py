from prometheus_client import Counter, Gauge, Histogram

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

LLM_FALLBACKS_TOTAL = Counter(
    "llm_fallbacks_total",
    "LLM fallback invocations",
    labelnames=["from_provider", "to_provider"],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    labelnames=["provider"],
)

EMBEDDINGS_REQUESTS_TOTAL = Counter(
    "embeddings_requests_total",
    "Total embedding requests",
    labelnames=["provider", "model", "kind", "outcome"],
)

EMBEDDINGS_DURATION_SECONDS = Histogram(
    "embeddings_duration_seconds",
    "Embedding request latency in seconds",
    labelnames=["provider", "model", "kind"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

EMBEDDINGS_VECTORS_TOTAL = Counter(
    "embeddings_vectors_total",
    "Total embedded vectors",
    labelnames=["provider", "model", "kind"],
)

RAG_CHUNKS_INDEXED_TOTAL = Counter(
    "rag_chunks_indexed_total",
    "Total RAG chunks indexed into Qdrant",
)

RAG_CHUNKS_SKIPPED_TOTAL = Counter(
    "rag_chunks_skipped_total",
    "Total RAG chunks skipped during ingestion",
    labelnames=["reason"],
)

RAG_SEARCH_REQUESTS_TOTAL = Counter(
    "rag_search_requests_total",
    "Total hybrid retrieval requests",
    labelnames=["outcome"],
)

RAG_SEARCH_DURATION_SECONDS = Histogram(
    "rag_search_duration_seconds",
    "Hybrid retrieval latency in seconds",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
