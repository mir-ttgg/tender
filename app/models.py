import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    templates: Mapped[list['Template']] = relationship(
        back_populates='user', cascade='all, delete-orphan', passive_deletes=True
    )


class DictionaryRegion(Base):
    __tablename__ = 'dictionary_regions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class DictionaryPlatform(Base):
    __tablename__ = 'dictionary_platforms'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class Template(Base):
    __tablename__ = 'templates'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    scoring_formula: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped['User'] = relationship(back_populates='templates')
    metrics: Mapped[list['Metric']] = relationship(
        back_populates='template_obj', cascade='all, delete-orphan', passive_deletes=True
    )


class Metric(Base):
    __tablename__ = 'metrics'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('templates.id', ondelete='CASCADE'), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    value_good_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value_good_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    value_bad_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value_bad_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    promt_snippet: Mapped[str | None] = mapped_column(String, nullable=True)
    promt_chouser: Mapped[str | None] = mapped_column(String, nullable=True)
    promt_valuation: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    template_obj: Mapped['Template'] = relationship(back_populates='metrics')


class Tender(Base):
    __tablename__ = 'tenders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    documents: Mapped[list['Document']] = relationship(
        back_populates='tender', cascade='all, delete-orphan', passive_deletes=True
    )


class Tender2TemplateFavorite(Base):
    __tablename__ = 'tender2template_favorites'

    tender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('tenders.id', ondelete='CASCADE'), primary_key=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('templates.id', ondelete='CASCADE'), primary_key=True
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Tender2Template2Metric(Base):
    __tablename__ = 'tender2template2metric'

    tender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('tenders.id', ondelete='CASCADE'), primary_key=True
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('templates.id', ondelete='CASCADE'), primary_key=True
    )
    metric_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('metrics.id', ondelete='CASCADE'), primary_key=True
    )
    result: Mapped[str | None] = mapped_column(String, nullable=True)


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('tenders.id', ondelete='CASCADE'), nullable=False, index=True
    )
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    format: Mapped[str | None] = mapped_column(String(32), nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    html_origin: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tender: Mapped['Tender'] = relationship(back_populates='documents')


class Template2Document2Metric(Base):
    __tablename__ = 'template2document2metrics'
    __table_args__ = (
        UniqueConstraint('template_id', 'document_id', 'metric_id', name='uq_template_document_metric'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey('templates.id', ondelete='CASCADE'), nullable=False, index=True
    )
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True
    )
    metric_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('metrics.id', ondelete='CASCADE'), nullable=False, index=True
    )
    metric_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metric_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_chosen: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value_score: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
