from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.core.deps import IssuerRepoDep, PaginationDep, SessionDep
from app.schemas.common import Page
from app.schemas.issuer import IssuerCreate, IssuerRead

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
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Issuer with code {data.code} already exists",
        ) from e
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
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete issuer with code {code}: linked risk reports exist",
        ) from e
