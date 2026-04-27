from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Metric,
    Template,
    Tender2Template2Metric,
    Tender2TemplateFavorite,
    Template2Document2Metric,
)
from app.schemas.template import MetricIn, TemplateUpdate, template_payload_fields


async def get_template_for_user(session: AsyncSession, template_id: UUID, user_id: int) -> Template:
    stmt = (
        select(Template)
        .options(selectinload(Template.metrics))
        .where(Template.id == template_id, Template.user_id == user_id)
    )
    template = await session.scalar(stmt)
    if template is None:
        logger.info('template not found', template_id=str(template_id), user_id=user_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='template not found')
    return template


async def list_templates(session: AsyncSession, user_id: int) -> list[Template]:
    stmt = select(Template).where(Template.user_id == user_id).order_by(Template.created_at.desc())
    result = await session.scalars(stmt)
    return list(result.all())


async def create_template(session: AsyncSession, user_id: int, name: str) -> Template:
    template = Template(user_id=user_id, name=name, template={}, scoring_formula=None)
    session.add(template)
    await session.commit()
    await session.refresh(template)
    logger.info('template created', template_id=str(template.id), user_id=user_id)
    return template


async def rename_template(
    session: AsyncSession, user_id: int, template_id: UUID, new_name: str
) -> Template:
    template = await get_template_for_user(session, template_id, user_id)
    template.name = new_name
    await session.commit()
    await session.refresh(template)
    logger.info('template renamed', template_id=str(template_id), name=new_name)
    return template


async def update_template(
    session: AsyncSession, user_id: int, template_id: UUID, payload: TemplateUpdate
) -> Template:
    template = await get_template_for_user(session, template_id, user_id)

    current_payload: dict[str, Any] = dict(template.template or {})
    incoming = payload.model_dump(exclude_unset=True)

    payload_changed = False
    for field in template_payload_fields():
        if field in incoming:
            new_value = incoming[field]
            if current_payload.get(field) != new_value:
                payload_changed = True
            current_payload[field] = new_value

    template.template = current_payload

    if 'scoring_formula' in incoming:
        template.scoring_formula = incoming['scoring_formula']

    if payload.metrics is not None:
        await _sync_metrics(session, template, payload.metrics)

    if payload_changed:
        await _invalidate_tender_results(session, template_id)

    await session.commit()
    await session.refresh(template, attribute_names=['metrics'])
    logger.info(
        'template updated',
        template_id=str(template_id),
        payload_changed=payload_changed,
        metrics_changed=payload.metrics is not None,
    )
    return template


async def _sync_metrics(session: AsyncSession, template: Template, incoming: list[MetricIn]) -> None:
    existing = {m.id: m for m in template.metrics}
    incoming_ids = {m.id for m in incoming if m.id is not None}

    removed_ids = [mid for mid in existing.keys() if mid not in incoming_ids]
    if removed_ids:
        await session.execute(delete(Metric).where(Metric.id.in_(removed_ids)))
        logger.info('metrics removed', template_id=str(template.id), count=len(removed_ids))

    invalidated_ids: list[int] = []
    for item in incoming:
        if item.id is not None and item.id in existing:
            metric = existing[item.id]
            changed = (
                metric.label != item.name
                or metric.value_good_name != item.value_good
                or metric.value_bad_name != item.value_bad
            )
            if changed:
                metric.label = item.name
                metric.value_good_name = item.value_good
                metric.value_bad_name = item.value_bad
                invalidated_ids.append(metric.id)
        else:
            metric = Metric(
                template_id=template.id,
                label=item.name,
                value_good_name=item.value_good,
                value_bad_name=item.value_bad,
            )
            session.add(metric)

    await session.flush()

    if invalidated_ids:
        await session.execute(
            delete(Tender2Template2Metric).where(
                Tender2Template2Metric.template_id == template.id,
                Tender2Template2Metric.metric_id.in_(invalidated_ids),
            )
        )
        await session.execute(
            delete(Template2Document2Metric).where(
                Template2Document2Metric.template_id == template.id,
                Template2Document2Metric.metric_id.in_(invalidated_ids),
            )
        )
        logger.info('metric results invalidated', template_id=str(template.id), count=len(invalidated_ids))


async def _invalidate_tender_results(session: AsyncSession, template_id: UUID) -> None:
    await session.execute(
        delete(Tender2TemplateFavorite).where(Tender2TemplateFavorite.template_id == template_id)
    )
    await session.execute(
        delete(Tender2Template2Metric).where(Tender2Template2Metric.template_id == template_id)
    )
    await session.execute(
        delete(Template2Document2Metric).where(Template2Document2Metric.template_id == template_id)
    )
    logger.info('template-wide results invalidated', template_id=str(template_id))
