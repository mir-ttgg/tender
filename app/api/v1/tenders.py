from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.tender import (
    DocumentDetail,
    TenderDetail,
    TenderListResponse,
)
from app.services import tender_service

router = APIRouter(prefix='/user/tender', tags=['tenders'])


@router.get('/list', response_model=TenderListResponse)
async def list_tenders(
    user: CurrentUser,
    session: DbSession,
    template_id: UUID = Query(...),
    page: int = Query(default=1, ge=0),
    is_favorite: bool | None = Query(default=None),
) -> TenderListResponse:
    return await tender_service.list_tenders(
        session, user.id, template_id, page, is_favorite
    )


@router.get('/{tender_id}', response_model=TenderDetail)
async def get_tender(
    tender_id: int, user: CurrentUser, session: DbSession
) -> TenderDetail:
    return await tender_service.get_tender_detail(session, user.id, tender_id)


@router.get('/{tender_id}/documents', response_model=list[DocumentDetail])
async def list_documents(
    tender_id: int, user: CurrentUser, session: DbSession
) -> list[DocumentDetail]:
    return await tender_service.list_tender_documents(session, user.id, tender_id)
