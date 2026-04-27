from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Document,
    Metric,
    Template,
    Tender,
    Tender2Template2Metric,
    Tender2TemplateFavorite,
    Template2Document2Metric,
)
from app.schemas.tender import (
    DocumentBrief,
    DocumentDetail,
    InlineMetric,
    MetricWithSnippets,
    Snippet,
    TenderDetail,
    TenderListItem,
    TenderListResponse,
)

PER_PAGE: int = 20


async def _ensure_template_owned(session: AsyncSession, template_id: UUID, user_id: int) -> Template:
    template = await session.scalar(
        select(Template).where(Template.id == template_id, Template.user_id == user_id)
    )
    if template is None:
        logger.info('template not owned', template_id=str(template_id), user_id=user_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='template not found')
    return template


def _tender_field(tender: Tender, key: str) -> Any:
    data: dict[str, Any] = tender.data or {}
    return data.get(key)


async def _build_inline_metrics(
    session: AsyncSession, template_id: UUID, tender_id: int
) -> list[InlineMetric]:
    rows = (
        await session.execute(
            select(Metric.label, Template2Document2Metric.value_name)
            .join(Template2Document2Metric, Template2Document2Metric.metric_id == Metric.id)
            .join(Document, Document.id == Template2Document2Metric.document_id)
            .where(
                Metric.template_id == template_id,
                Template2Document2Metric.template_id == template_id,
                Template2Document2Metric.is_chosen.is_(True),
                Document.tender_id == tender_id,
            )
        )
    ).all()
    return [InlineMetric(label=label, value=value) for label, value in rows]


async def list_tenders(
    session: AsyncSession,
    user_id: int,
    template_id: UUID,
    page: int,
    is_favorite: bool | None,
) -> TenderListResponse:
    template = await _ensure_template_owned(session, template_id, user_id)

    page = max(page, 1)

    base_filters = [Tender2TemplateFavorite.template_id == template_id]
    if is_favorite is not None:
        base_filters.append(Tender2TemplateFavorite.is_favorite.is_(is_favorite))

    total = await session.scalar(
        select(func.count())
        .select_from(Tender2TemplateFavorite)
        .where(*base_filters)
    ) or 0
    pages = max((total + PER_PAGE - 1) // PER_PAGE, 1)

    rows = (
        await session.execute(
            select(Tender, Tender2TemplateFavorite.score)
            .join(Tender2TemplateFavorite, Tender2TemplateFavorite.tender_id == Tender.id)
            .where(*base_filters)
            .order_by(Tender.id.desc())
            .offset((page - 1) * PER_PAGE)
            .limit(PER_PAGE)
        )
    ).all()

    tenders: list[TenderListItem] = []
    for tender, score in rows:
        inline_metrics = await _build_inline_metrics(session, template_id, tender.id)
        tenders.append(
            TenderListItem(
                id=tender.id,
                price=_tender_field(tender, 'price'),
                currency=_tender_field(tender, 'currency'),
                platform_id=_tender_field(tender, 'platform_id'),
                platform_url=_tender_field(tender, 'platform_url'),
                scoring=score,
                finish_at=_tender_field(tender, 'finish_at'),
                organization_name=_tender_field(tender, 'organization_name'),
                title=_tender_field(tender, 'title'),
                delivery_location=_tender_field(tender, 'delivery_location'),
                trade_type=_tender_field(tender, 'trade_type'),
                inn=_tender_field(tender, 'inn'),
                published_at=_tender_field(tender, 'published_at'),
                metrics=inline_metrics,
            )
        )

    logger.info(
        'tender list',
        user_id=user_id,
        template_id=str(template_id),
        page=page,
        pages=pages,
        total=total,
    )

    return TenderListResponse(
        page=page,
        pages=pages,
        scoring_formula=template.scoring_formula,
        tenders=tenders,
    )


async def _accessible_template_id(
    session: AsyncSession, user_id: int, tender_id: int
) -> UUID | None:
    return await session.scalar(
        select(Tender2TemplateFavorite.template_id)
        .join(Template, Template.id == Tender2TemplateFavorite.template_id)
        .where(Tender2TemplateFavorite.tender_id == tender_id, Template.user_id == user_id)
        .limit(1)
    )


async def get_tender_detail(
    session: AsyncSession, user_id: int, tender_id: int
) -> TenderDetail:
    tender = await session.scalar(select(Tender).where(Tender.id == tender_id))
    if tender is None:
        logger.info('tender not found', tender_id=tender_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='tender not found')

    template_id = await _accessible_template_id(session, user_id, tender_id)
    if template_id is None:
        logger.info('tender forbidden', tender_id=tender_id, user_id=user_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='tender not accessible')

    score = await session.scalar(
        select(Tender2TemplateFavorite.score).where(
            Tender2TemplateFavorite.tender_id == tender_id,
            Tender2TemplateFavorite.template_id == template_id,
        )
    )

    documents = (
        await session.scalars(
            select(Document).where(Document.tender_id == tender_id).order_by(Document.id.asc())
        )
    ).all()

    metrics = (
        await session.scalars(
            select(Metric).where(Metric.template_id == template_id).order_by(Metric.id.asc())
        )
    ).all()

    document_ids = [d.id for d in documents]
    snippet_rows: list[Template2Document2Metric] = []
    if document_ids:
        snippet_rows = list(
            (
                await session.scalars(
                    select(Template2Document2Metric).where(
                        Template2Document2Metric.template_id == template_id,
                        Template2Document2Metric.document_id.in_(document_ids),
                    )
                )
            ).all()
        )

    snippets_by_metric: dict[int, list[Template2Document2Metric]] = {}
    for row in snippet_rows:
        snippets_by_metric.setdefault(row.metric_id, []).append(row)

    metric_blocks: list[MetricWithSnippets] = []
    for metric in metrics:
        items = snippets_by_metric.get(metric.id, [])
        items.sort(key=lambda r: (not bool(r.is_chosen), r.id))
        metric_blocks.append(
            MetricWithSnippets(
                id=metric.id,
                label=metric.label,
                snippets=[
                    Snippet(
                        id=row.id,
                        document_id=row.document_id,
                        is_choosen=row.is_chosen,
                        value=row.value_name,
                    )
                    for row in items
                ],
            )
        )

    return TenderDetail(
        id=tender.id,
        price=_tender_field(tender, 'price'),
        currency=_tender_field(tender, 'currency'),
        platform_id=_tender_field(tender, 'platform_id'),
        platform_url=_tender_field(tender, 'platform_url'),
        scoring=score,
        finish_at=_tender_field(tender, 'finish_at'),
        organization_name=_tender_field(tender, 'organization_name'),
        title=_tender_field(tender, 'title'),
        delivery_location=_tender_field(tender, 'delivery_location'),
        trade_type=_tender_field(tender, 'trade_type'),
        inn=_tender_field(tender, 'inn'),
        published_at=_tender_field(tender, 'published_at'),
        description=_tender_field(tender, 'description'),
        documents=[
            DocumentBrief(id=d.id, filename=d.filename, format=d.format, url=d.url)
            for d in documents
        ],
        metrics=metric_blocks,
    )


def _inject_snippets(html: str, ranges: list[Template2Document2Metric]) -> str:
    valid = [
        r
        for r in ranges
        if r.metric_start is not None and r.metric_end is not None and r.metric_end > r.metric_start
    ]
    valid.sort(key=lambda r: r.metric_start, reverse=True)
    result = html
    for row in valid:
        start = row.metric_start
        end = row.metric_end
        if start < 0 or end > len(result):
            continue
        marker_open = f'<div class="snippet_id-{row.id}">'
        marker_close = '</div>'
        result = result[:start] + marker_open + result[start:end] + marker_close + result[end:]
    return result


async def list_tender_documents(
    session: AsyncSession, user_id: int, tender_id: int
) -> list[DocumentDetail]:
    template_id = await _accessible_template_id(session, user_id, tender_id)
    if template_id is None:
        if await session.scalar(select(Tender.id).where(Tender.id == tender_id)) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='tender not found')
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='tender not accessible')

    documents = list(
        (
            await session.scalars(
                select(Document).where(Document.tender_id == tender_id).order_by(Document.id.asc())
            )
        ).all()
    )

    document_ids = [d.id for d in documents]
    ranges_by_doc: dict[int, list[Template2Document2Metric]] = {}
    if document_ids:
        rows = (
            await session.scalars(
                select(Template2Document2Metric).where(
                    Template2Document2Metric.template_id == template_id,
                    Template2Document2Metric.document_id.in_(document_ids),
                )
            )
        ).all()
        for row in rows:
            ranges_by_doc.setdefault(row.document_id, []).append(row)

    return [
        DocumentDetail(
            id=d.id,
            filename=d.filename,
            format=d.format,
            url=d.url,
            html=_inject_snippets(d.html_origin or '', ranges_by_doc.get(d.id, [])),
        )
        for d in documents
    ]


# Kept for backward use by Tender2Template2Metric (not used in new endpoints, but referenced).
__all__ = (
    'list_tenders',
    'get_tender_detail',
    'list_tender_documents',
    'Tender2Template2Metric',
)
