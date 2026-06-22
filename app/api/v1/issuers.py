from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.core.deps import HybridRetrieverDep, IssuerRepoDep, PaginationDep, SessionDep
from app.db.enums import DocumentType
from app.schemas.common import Page
from app.schemas.issuer import IssuerCreate, IssuerRead
from app.schemas.retrieval import SearchResponse

router = APIRouter(prefix="/issuers", tags=["issuers"])


@router.get("", response_model=Page[IssuerRead])
async def list_issuers(
    pagination: PaginationDep,
    repo: IssuerRepoDep,
    is_public: bool | None = Query(default=None),
) -> Page[IssuerRead]:
    items, total = await repo.list(
        limit=pagination.limit,
        offset=pagination.offset,
        is_public=is_public,
    )
    return Page(
        items=[IssuerRead.model_validate(item) for item in items],
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
    )


@router.post("", response_model=IssuerRead, status_code=status.HTTP_201_CREATED)
async def create_issuer(
    data: IssuerCreate,
    repo: IssuerRepoDep,
    session: SessionDep,
) -> IssuerRead:
    try:
        issuer = await repo.create(data)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Issuer with code {data.code} already exists",
        ) from exc
    return IssuerRead.model_validate(issuer)


@router.get("/{code}", response_model=IssuerRead)
async def get_issuer_by_code(
    code: str,
    repo: IssuerRepoDep,
) -> IssuerRead:
    issuer = await repo.get_by_code(code)
    if not issuer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer with code {code} not found",
        )
    return IssuerRead.model_validate(issuer)


@router.get("/{code}/search", response_model=SearchResponse)
async def search_issuer_documents(
    code: str,
    retriever: HybridRetrieverDep,
    issuer_repo: IssuerRepoDep,
    q: str = Query(min_length=1, max_length=512),
    limit: int = Query(default=10, ge=1, le=50),
    doc_type: DocumentType | None = Query(default=None),
) -> SearchResponse:
    issuer = await issuer_repo.get_by_code(code)
    if issuer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer with code {code} not found",
        )

    results = await retriever.retrieve(
        q,
        issuer=issuer.code,
        doc_type=doc_type,
        limit=limit,
    )
    return SearchResponse(query=q, issuer_code=issuer.code, results=results)


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_issuer(
    code: str,
    repo: IssuerRepoDep,
    session: SessionDep,
) -> None:
    issuer = await repo.get_by_code(code)
    if not issuer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer with code {code} not found",
        )
    try:
        await repo.delete(issuer)
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete issuer with code {code}: linked risk reports exist",
        ) from exc
