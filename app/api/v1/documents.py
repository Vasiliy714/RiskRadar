from datetime import datetime

from fastapi import APIRouter, Body, Header, HTTPException, Query, status

from app.core.deps import IngestionServiceDep, IssuerRepoDep
from app.db.enums import DocumentType
from app.rag.parsers import SourceFormat, detect_source_format
from app.schemas.ingestion import IngestDocumentRequest, IngestDocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=IngestDocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    data: IngestDocumentRequest,
    issuer_repo: IssuerRepoDep,
    ingestion_service: IngestionServiceDep,
) -> IngestDocumentResponse:
    issuer = await issuer_repo.get_by_code(data.issuer_code)
    if issuer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer with code {data.issuer_code} not found",
        )

    document, job, stats = await ingestion_service.ingest_text(
        issuer=issuer,
        doc_type=data.doc_type,
        title=data.title,
        text=data.text,
        period_key=data.period_key,
        source_url=data.source_url,
        published_at=data.published_at,
    )

    return IngestDocumentResponse(
        document_id=document.id,
        ingestion_job_id=job.id,
        status=job.status,
        chunks_total=stats.chunks_total,
        chunks_indexed=stats.chunks_indexed,
        chunks_skipped_duplicate=stats.chunks_skipped_duplicate,
        idempotent=bool(job.payload.get("idempotent")),
    )


@router.post(
    "/ingest/upload",
    response_model=IngestDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_document_upload(
    issuer_repo: IssuerRepoDep,
    ingestion_service: IngestionServiceDep,
    body: bytes = Body(...),
    issuer_code: str = Query(...),
    doc_type: DocumentType = Query(...),
    title: str = Query(...),
    period_key: str = Query(...),
    source_url: str | None = Query(default=None),
    published_at: datetime | None = Query(default=None),
    filename: str | None = Query(default=None),
    content_type: str | None = Header(default=None, alias="Content-Type"),
) -> IngestDocumentResponse:
    issuer = await issuer_repo.get_by_code(issuer_code)
    if issuer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer with code {issuer_code} not found",
        )

    source_format = detect_source_format(
        filename=filename,
        content_type=content_type,
    )

    if source_format in {SourceFormat.TEXT, SourceFormat.HTML}:
        raw_content: str | bytes = body.decode("utf-8")
        preview_text = str(raw_content)
    else:
        raw_content = body
        preview_text = filename or title

    document, job, stats = await ingestion_service.ingest_text(
        issuer=issuer,
        doc_type=doc_type,
        title=title,
        text=preview_text,
        period_key=period_key,
        source_url=source_url,
        published_at=published_at,
        source_format=source_format,
        raw_content=raw_content,
    )

    return IngestDocumentResponse(
        document_id=document.id,
        ingestion_job_id=job.id,
        status=job.status,
        chunks_total=stats.chunks_total,
        chunks_indexed=stats.chunks_indexed,
        chunks_skipped_duplicate=stats.chunks_skipped_duplicate,
        idempotent=bool(job.payload.get("idempotent")),
    )
