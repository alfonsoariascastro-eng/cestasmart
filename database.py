import json
import os
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, Float, Text,
    DateTime, ForeignKey, UniqueConstraint, select, func
)
from sqlalchemy.exc import SQLAlchemyError


def _db_url():
    url=os.environ.get("DATABASE_URL", "sqlite:///cestasmart_local.db")
    if url.startswith("postgres://"):
        url="postgresql+psycopg://"+url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url="postgresql+psycopg://"+url[len("postgresql://"):]
    return url

engine=create_engine(_db_url(), pool_pre_ping=True, future=True)
metadata=MetaData()

products=Table(
    "products", metadata,
    Column("id", Integer, primary_key=True),
    Column("store", String(40), nullable=False),
    Column("provider_product_id", String(120)),
    Column("ean", String(20)),
    Column("name", Text, nullable=False),
    Column("brand", String(160)),
    Column("category", String(240)),
    Column("latest_price", Float),
    Column("normalized_price", Float),
    Column("confidence", String(20)),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("store","provider_product_id",name="uq_product_store_provider")
)

price_snapshots=Table(
    "price_snapshots", metadata,
    Column("id", Integer, primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
    Column("price", Float, nullable=False),
    Column("normalized_price", Float),
    Column("observed_at", DateTime(timezone=True), nullable=False)
)

search_events=Table(
    "search_events", metadata,
    Column("id", Integer, primary_key=True),
    Column("store", String(40), nullable=False),
    Column("query", Text, nullable=False),
    Column("ean", String(20)),
    Column("results_count", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), nullable=False)
)

comparison_events=Table(
    "comparison_events", metadata,
    Column("id", Integer, primary_key=True),
    Column("request_json", Text, nullable=False),
    Column("result_json", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False)
)


def init_db():
    metadata.create_all(engine)


def now():
    return datetime.now(timezone.utc)


def save_search(store, query, ean, payload):
    """Persist live search results into the canonical catalog and price history."""
    ts=now()
    rows=payload.get("products") or []
    with engine.begin() as conn:
        conn.execute(search_events.insert().values(
            store=store, query=query, ean=ean or None,
            results_count=len(rows), created_at=ts
        ))
        for p in rows:
            provider_id=str(p.get("id")) if p.get("id") is not None else None
            pean=str(p.get("ean") or p.get("gtin") or "") or None
            name=str(p.get("name") or "").strip()
            if not name:
                continue
            existing=None
            if provider_id:
                existing=conn.execute(select(products.c.id, products.c.latest_price).where(
                    products.c.store==store,
                    products.c.provider_product_id==provider_id
                )).first()
            if not existing and pean:
                existing=conn.execute(select(products.c.id, products.c.latest_price).where(
                    products.c.store==store,
                    products.c.ean==pean
                )).first()
            if not existing:
                existing=conn.execute(select(products.c.id, products.c.latest_price).where(
                    products.c.store==store,
                    products.c.name==name
                )).first()

            values=dict(
                store=store, provider_product_id=provider_id, ean=pean,
                name=name, brand=p.get("brand"),
                category=str(p.get("category")) if p.get("category") else None,
                latest_price=p.get("price"), normalized_price=p.get("normalized_price"),
                confidence=p.get("confidence"), updated_at=ts
            )
            if existing:
                pid=existing.id
                conn.execute(products.update().where(products.c.id==pid).values(**values))
            else:
                pid=conn.execute(products.insert().values(**values)).inserted_primary_key[0]

            price=p.get("price")
            if price is not None:
                # Append a snapshot only if this exact price wasn't the latest stored one.
                last=conn.execute(select(price_snapshots.c.price).where(
                    price_snapshots.c.product_id==pid
                ).order_by(price_snapshots.c.observed_at.desc()).limit(1)).scalar_one_or_none()
                if last is None or float(last)!=float(price):
                    conn.execute(price_snapshots.insert().values(
                        product_id=pid, price=float(price),
                        normalized_price=p.get("normalized_price"), observed_at=ts
                    ))


def save_comparison(request_payload, result_payload):
    with engine.begin() as conn:
        conn.execute(comparison_events.insert().values(
            request_json=json.dumps(request_payload, ensure_ascii=False),
            result_json=json.dumps(result_payload, ensure_ascii=False),
            created_at=now()
        ))


def catalog_stats():
    with engine.connect() as conn:
        return {
            "products": int(conn.execute(select(func.count()).select_from(products)).scalar_one()),
            "price_snapshots": int(conn.execute(select(func.count()).select_from(price_snapshots)).scalar_one()),
            "searches": int(conn.execute(select(func.count()).select_from(search_events)).scalar_one()),
            "comparisons": int(conn.execute(select(func.count()).select_from(comparison_events)).scalar_one()),
        }
