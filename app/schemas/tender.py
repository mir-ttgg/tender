from pydantic import BaseModel


class InlineMetric(BaseModel):
    label: str
    value: str | None = None


class TenderListItem(BaseModel):
    id: int
    price: float | None = None
    currency: str | None = None
    platform_id: int | None = None
    platform_url: str | None = None
    scoring: int | None = None
    finish_at: str | None = None
    organization_name: str | None = None
    title: str | None = None
    delivery_location: str | None = None
    trade_type: str | None = None
    inn: int | None = None
    published_at: str | None = None
    metrics: list[InlineMetric] = []


class TenderListResponse(BaseModel):
    page: int
    pages: int
    scoring_formula: str | None = None
    tenders: list[TenderListItem]


class DocumentBrief(BaseModel):
    id: int
    filename: str | None = None
    format: str | None = None
    url: str | None = None


class Snippet(BaseModel):
    id: int
    document_id: int
    is_choosen: bool | None = None
    value: str | None = None


class MetricWithSnippets(BaseModel):
    id: int
    label: str
    snippets: list[Snippet]


class TenderDetail(BaseModel):
    id: int
    price: float | None = None
    currency: str | None = None
    platform_id: int | None = None
    platform_url: str | None = None
    scoring: int | None = None
    finish_at: str | None = None
    organization_name: str | None = None
    title: str | None = None
    delivery_location: str | None = None
    trade_type: str | None = None
    inn: int | None = None
    published_at: str | None = None
    description: str | None = None
    documents: list[DocumentBrief]
    metrics: list[MetricWithSnippets]


class DocumentDetail(BaseModel):
    id: int
    filename: str | None = None
    format: str | None = None
    url: str | None = None
    html: str | None = None
