from uuid import UUID

from fastapi import APIRouter, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.template import (
    TemplateCreate,
    TemplateCreateResponse,
    TemplateListItem,
    TemplateOut,
    TemplateRename,
    TemplateUpdate,
    template_to_out,
)
from app.services import template_service

router = APIRouter(prefix='/user/template', tags=['templates'])


@router.get('/list', response_model=list[TemplateListItem])
async def list_templates(user: CurrentUser, session: DbSession) -> list[TemplateListItem]:
    templates = await template_service.list_templates(session, user.id)
    return [TemplateListItem(id=t.id, name=t.name) for t in templates]


@router.post(
    '/create',
    response_model=TemplateCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    payload: TemplateCreate, user: CurrentUser, session: DbSession
) -> TemplateCreateResponse:
    template = await template_service.create_template(session, user.id, payload.name)
    return TemplateCreateResponse(id=template.id)


@router.patch('/rename', status_code=status.HTTP_204_NO_CONTENT)
async def rename_template(
    payload: TemplateRename, user: CurrentUser, session: DbSession
) -> None:
    await template_service.rename_template(
        session, user.id, payload.template_id, payload.name
    )


@router.get('/{template_id}', response_model=TemplateOut)
async def get_template(
    template_id: UUID, user: CurrentUser, session: DbSession
) -> TemplateOut:
    template = await template_service.get_template_for_user(session, template_id, user.id)
    return template_to_out(template)


@router.put('/{template_id}', status_code=status.HTTP_204_NO_CONTENT)
async def update_template(
    template_id: UUID,
    payload: TemplateUpdate,
    user: CurrentUser,
    session: DbSession,
) -> None:
    await template_service.update_template(session, user.id, template_id, payload)
