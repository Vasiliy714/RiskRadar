__all__ = ["DocumentIngestionService", "HybridRetriever", "VectorIndexService"]


def __getattr__(name: str) -> object:
    if name == "DocumentIngestionService":
        from app.rag.ingestion import DocumentIngestionService

        return DocumentIngestionService
    if name == "HybridRetriever":
        from app.rag.retriever import HybridRetriever

        return HybridRetriever
    if name == "VectorIndexService":
        from app.rag.vector_index import VectorIndexService

        return VectorIndexService
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
