from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MetricIn(BaseModel):
    id: int | None = None
    name: str
    value_good: str | None = None
    value_bad: str | None = None


class MetricOut(BaseModel):
    id: int
    name: str
    value_good: str | None
    value_bad: str | None

    model_config = ConfigDict(from_attributes=True)


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class TemplateRename(BaseModel):
    template_id: UUID
    name: str = Field(min_length=1, max_length=255)


class TemplateUpdate(BaseModel):
    keywords_good: list[str] | None = None
    keywords_bad: list[str] | None = None
    trade_types: list[str] | None = None
    inn_only: list[int] | None = None
    region_id: list[int] | None = None
    platform_id: list[int] | None = None
    price_from: int | None = None
    metrics: list[MetricIn] | None = None
    scoring_formula: str | None = None


class TemplateOut(BaseModel):
    uuid: UUID
    name: str
    keywords_good: list[str] | None = None
    keywords_bad: list[str] | None = None
    trade_types: list[str] | None = None
    inn_only: list[int] | None = None
    region_id: list[int] | None = None
    platform_id: list[int] | None = None
    price_from: int | None = None
    metrics: list[MetricOut] = Field(default_factory=list)
    scoring_formula: str | None = None


class TemplateListItem(BaseModel):
    id: UUID
    name: str


class TemplateCreateResponse(BaseModel):
    id: UUID


def template_payload_fields() -> tuple[str, ...]:
    return (
        'keywords_good',
        'keywords_bad',
        'trade_types',
        'inn_only',
        'region_id',
        'platform_id',
        'price_from',
    )


def template_to_out(template: Any) -> TemplateOut:
    payload: dict[str, Any] = template.template or {}
    metrics_out = [
        MetricOut(
            id=m.id,
            name=m.label,
            value_good=m.value_good_name,
            value_bad=m.value_bad_name,
        )
        for m in template.metrics
    ]
    return TemplateOut(
        uuid=template.id,
        name=template.name,
        keywords_good=payload.get('keywords_good'),
        keywords_bad=payload.get('keywords_bad'),
        trade_types=payload.get('trade_types'),
        inn_only=payload.get('inn_only'),
        region_id=payload.get('region_id'),
        platform_id=payload.get('platform_id'),
        price_from=payload.get('price_from'),
        metrics=metrics_out,
        scoring_formula=template.scoring_formula,
    )
