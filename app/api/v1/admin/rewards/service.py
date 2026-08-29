from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.rewards.schemas import (
    PointPackageCreateRequest,
    PointPackageList,
    PointPackageResponse,
    PointPackageUpdateRequest,
    PromoCodeCreateRequest,
    PromoCodeList,
    PromoCodeResponse,
    PromoCodeUpdateRequest,
    PromoRedemptionList,
    PromoRedemptionResponse,
    RewardOfferCreateRequest,
    RewardOfferList,
    RewardOfferResponse,
    RewardOfferUpdateRequest,
    RewardTradeList,
    RewardTradeResponse,
)
from app.core.errors import conflict, not_found
from app.core.pagination import clamp_page
from app.models.promo import PromoCode, PromoRedemption
from app.models.rewards import PointPackage, RewardOffer, RewardTrade
from app.services.reward_offers import normalize_expires_at, utc_now


def _offer_response(row: RewardOffer) -> RewardOfferResponse:
    return RewardOfferResponse(
        id=str(row.id),
        code=row.code,
        kind=row.kind,
        points_cost=row.points_cost,
        percent_off=row.percent_off,
        free_minutes=row.free_minutes,
        min_tier=row.min_tier,
        max_tier=row.max_tier,
        is_welcome_gift=row.is_welcome_gift,
        is_active=row.is_active,
        expires_at=row.expires_at,
        created_at=row.created_at,
    )


def _offer_snapshot(row: RewardOffer) -> dict[str, Any]:
    return _offer_response(row).model_dump(mode="json")


def _promo_response(row: PromoCode) -> PromoCodeResponse:
    return PromoCodeResponse(
        id=str(row.id),
        code=row.code,
        percent_off=row.percent_off,
        fixed_amount=Decimal(row.fixed_amount) if row.fixed_amount is not None else None,
        max_redemptions=row.max_redemptions,
        redemption_count=row.redemption_count,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        is_active=row.is_active,
        created_at=row.created_at,
    )


def _promo_snapshot(row: PromoCode) -> dict[str, Any]:
    return _promo_response(row).model_dump(mode="json")


def list_reward_offers(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    include_expired: bool = True,
) -> RewardOfferList:
    page, page_size = clamp_page(page, page_size)
    query = db.query(RewardOffer)
    if not include_expired:
        now = utc_now()
        query = query.filter(
            or_(
                RewardOffer.expires_at.is_(None),
                RewardOffer.expires_at > now,
            )
        )
    total = query.with_entities(func.count(RewardOffer.id)).scalar() or 0
    rows = (
        query.order_by(RewardOffer.created_at.desc(), RewardOffer.code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return RewardOfferList(
        items=[_offer_response(row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def create_reward_offer(
    db: Session,
    payload: RewardOfferCreateRequest,
    admin: AdminPrincipal,
) -> RewardOfferResponse:
    code = payload.code.strip().lower()
    if db.query(RewardOffer.id).filter(RewardOffer.code == code).first() is not None:
        raise conflict("Reward offer code already exists")
    data = payload.model_dump(exclude={"code", "expires_at"})
    row = RewardOffer(
        **data,
        code=code,
        expires_at=normalize_expires_at(payload.expires_at, reject_past=True),
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        admin_user_id=admin.id,
        action="reward_offer.create",
        entity_type="reward_offer",
        entity_id=row.id,
        after=_offer_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _offer_response(row)


def update_reward_offer(
    db: Session,
    offer_id: UUID,
    payload: RewardOfferUpdateRequest,
    admin: AdminPrincipal,
) -> RewardOfferResponse:
    row = db.get(RewardOffer, offer_id)
    if row is None:
        raise not_found("Reward offer")
    before = _offer_snapshot(row)
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes:
        code = changes["code"].strip().lower()
        duplicate = (
            db.query(RewardOffer.id)
            .filter(RewardOffer.code == code, RewardOffer.id != offer_id)
            .first()
        )
        if duplicate is not None:
            raise conflict("Reward offer code already exists")
        changes["code"] = code
    if "expires_at" in payload.model_fields_set:
        changes["expires_at"] = normalize_expires_at(payload.expires_at, reject_past=False)
    for field, value in changes.items():
        setattr(row, field, value)
    write_audit(
        db,
        admin_user_id=admin.id,
        action="reward_offer.update",
        entity_type="reward_offer",
        entity_id=row.id,
        before=before,
        after=_offer_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _offer_response(row)


def list_reward_trades(
    db: Session, *, page: int = 1, page_size: int = 20
) -> RewardTradeList:
    page, page_size = clamp_page(page, page_size)
    query = db.query(RewardTrade)
    total = query.with_entities(func.count(RewardTrade.id)).scalar() or 0
    rows = (
        query.order_by(RewardTrade.traded_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return RewardTradeList(
        items=[
            RewardTradeResponse(
                id=str(row.id),
                ventor_id=str(row.ventor_id),
                offer_id=str(row.offer_id),
                points_spent=row.points_spent,
                is_welcome_gift=row.is_welcome_gift,
                traded_at=row.traded_at,
            )
            for row in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def list_promo_codes(
    db: Session, *, page: int = 1, page_size: int = 20
) -> PromoCodeList:
    page, page_size = clamp_page(page, page_size)
    query = db.query(PromoCode)
    total = query.with_entities(func.count(PromoCode.id)).scalar() or 0
    rows = (
        query.order_by(PromoCode.created_at.desc(), PromoCode.code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PromoCodeList(
        items=[_promo_response(row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def create_promo_code(
    db: Session,
    payload: PromoCodeCreateRequest,
    admin: AdminPrincipal,
) -> PromoCodeResponse:
    code = payload.code.strip().upper()
    if db.query(PromoCode.id).filter(PromoCode.code == code).first() is not None:
        raise conflict("Promo code already exists")
    row = PromoCode(**payload.model_dump(exclude={"code"}), code=code)
    db.add(row)
    db.flush()
    write_audit(
        db,
        admin_user_id=admin.id,
        action="promo_code.create",
        entity_type="promo_code",
        entity_id=row.id,
        after=_promo_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _promo_response(row)


def update_promo_code(
    db: Session,
    promo_id: UUID,
    payload: PromoCodeUpdateRequest,
    admin: AdminPrincipal,
) -> PromoCodeResponse:
    row = db.get(PromoCode, promo_id)
    if row is None:
        raise not_found("Promo code")
    before = _promo_snapshot(row)
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes:
        code = changes["code"].strip().upper()
        duplicate = (
            db.query(PromoCode.id)
            .filter(PromoCode.code == code, PromoCode.id != promo_id)
            .first()
        )
        if duplicate is not None:
            raise conflict("Promo code already exists")
        changes["code"] = code
    for field, value in changes.items():
        setattr(row, field, value)
    write_audit(
        db,
        admin_user_id=admin.id,
        action="promo_code.update",
        entity_type="promo_code",
        entity_id=row.id,
        before=before,
        after=_promo_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _promo_response(row)


def list_promo_redemptions(
    db: Session,
    promo_id: UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> PromoRedemptionList:
    if db.get(PromoCode, promo_id) is None:
        raise not_found("Promo code")
    page, page_size = clamp_page(page, page_size)
    query = db.query(PromoRedemption).filter(
        PromoRedemption.promo_code_id == promo_id
    )
    total = query.with_entities(func.count(PromoRedemption.id)).scalar() or 0
    rows = (
        query.order_by(PromoRedemption.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PromoRedemptionList(
        items=[
            PromoRedemptionResponse(
                id=str(row.id),
                promo_code_id=str(row.promo_code_id),
                ventor_id=str(row.ventor_id),
                session_id=str(row.session_id) if row.session_id else None,
                discount_amount=Decimal(row.discount_amount),
                created_at=row.created_at,
            )
            for row in rows
        ],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def _point_package_response(row: PointPackage) -> PointPackageResponse:
    return PointPackageResponse(
        id=str(row.id),
        code=row.code,
        points=row.points,
        price_usd=Decimal(row.price_usd),
        bonus_percent=row.bonus_percent,
        sort_order=row.sort_order,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _point_package_snapshot(row: PointPackage) -> dict[str, Any]:
    return _point_package_response(row).model_dump(mode="json")


def list_point_packages(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
) -> PointPackageList:
    page, page_size = clamp_page(page, page_size)
    query = db.query(PointPackage)
    if active_only:
        query = query.filter(PointPackage.is_active.is_(True))
    total = query.with_entities(func.count(PointPackage.id)).scalar() or 0
    rows = (
        query.order_by(PointPackage.sort_order.asc(), PointPackage.code.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PointPackageList(
        items=[_point_package_response(row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def create_point_package(
    db: Session,
    payload: PointPackageCreateRequest,
    admin: AdminPrincipal,
) -> PointPackageResponse:
    code = payload.code.strip()
    duplicate = db.query(PointPackage.id).filter(PointPackage.code == code).first()
    if duplicate is not None:
        raise conflict("Point package code already exists")
    row = PointPackage(
        code=code,
        points=payload.points,
        price_usd=payload.price_usd,
        bonus_percent=payload.bonus_percent,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(row)
    db.flush()
    write_audit(
        db,
        admin_user_id=admin.id,
        action="point_package.create",
        entity_type="point_package",
        entity_id=row.id,
        after=_point_package_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _point_package_response(row)


def update_point_package(
    db: Session,
    package_id: UUID,
    payload: PointPackageUpdateRequest,
    admin: AdminPrincipal,
) -> PointPackageResponse:
    row = db.get(PointPackage, package_id)
    if row is None:
        raise not_found("Point package")
    before = _point_package_snapshot(row)
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes:
        code = changes["code"].strip()
        duplicate = (
            db.query(PointPackage.id)
            .filter(PointPackage.code == code, PointPackage.id != package_id)
            .first()
        )
        if duplicate is not None:
            raise conflict("Point package code already exists")
        changes["code"] = code
    for field, value in changes.items():
        setattr(row, field, value)
    write_audit(
        db,
        admin_user_id=admin.id,
        action="point_package.update",
        entity_type="point_package",
        entity_id=row.id,
        before=before,
        after=_point_package_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _point_package_response(row)
