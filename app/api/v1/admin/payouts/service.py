from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.admin.audit import write_audit
from app.api.v1.admin.deps import AdminPrincipal
from app.api.v1.admin.payouts.schemas import (
    AdjustWalletRequest,
    ApprovePayoutRequest,
    EarningsTiersResponse,
    PayoutDetailResponse,
    PayoutListResponse,
    PayoutMethodResponse,
    PayoutResponse,
    RejectPayoutRequest,
    WalletAdjustmentResponse,
    WalletLedgerEntryResponse,
    WalletResponse,
)
from app.core.errors import conflict, not_found, validation_error
from app.core.pagination import Paginated, clamp_page
from app.models.admin import AppConfigKv
from app.models.earnings import (
    ListenerWallet,
    Payout,
    PayoutMethod,
    WalletLedgerEntry,
)
from app.models.enums import LedgerEntryType, PayoutStatus

DEFAULT_EARNINGS_TIERS = {
    "starter": {"rate_per_minute": 0.25, "min_sessions": 0},
    "rising": {"rate_per_minute": 0.35, "min_sessions": 25},
    "trusted": {"rate_per_minute": 0.45, "min_sessions": 100},
    "expert": {"rate_per_minute": 0.55, "min_sessions": 250},
    "elite": {"rate_per_minute": 0.70, "min_sessions": 500},
}


def _payout_response(row: Payout) -> PayoutResponse:
    return PayoutResponse(
        id=str(row.id),
        listener_id=str(row.listener_id),
        amount=Decimal(row.amount),
        status=row.status,
        method_label=row.method_label,
        reference=row.reference,
        requested_at=row.requested_at,
        processed_at=row.processed_at,
        failure_reason=row.failure_reason,
        reviewed_by_admin_id=(
            str(row.reviewed_by_admin_id) if row.reviewed_by_admin_id else None
        ),
    )


def _mask_last_four(value: str | None) -> str | None:
    if value is None:
        return None
    return f"****{value[-4:]}"


def _ledger_response(row: WalletLedgerEntry) -> WalletLedgerEntryResponse:
    return WalletLedgerEntryResponse(
        id=str(row.id),
        type=row.type,
        amount=Decimal(row.amount),
        balance_after=Decimal(row.balance_after),
        session_id=str(row.session_id) if row.session_id else None,
        payout_id=str(row.payout_id) if row.payout_id else None,
        idempotency_key=row.idempotency_key,
        note=row.note,
        created_at=row.created_at,
    )


def list_payouts(
    db: Session,
    *,
    status: PayoutStatus = PayoutStatus.pending,
    page: int = 1,
    page_size: int = 20,
) -> PayoutListResponse:
    page, page_size = clamp_page(page, page_size)
    query = db.query(Payout).filter(Payout.status == status)
    total = query.with_entities(func.count(Payout.id)).scalar() or 0
    rows = (
        query.order_by(Payout.requested_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PayoutListResponse(
        items=[_payout_response(row) for row in rows],
        total=int(total),
        page=page,
        page_size=page_size,
    )


def get_payout(db: Session, payout_id: UUID) -> PayoutDetailResponse:
    payout = db.get(Payout, payout_id)
    if payout is None:
        raise not_found("Payout")
    method = db.get(PayoutMethod, payout.payout_method_id)
    if method is None:
        raise not_found("Payout method")
    return PayoutDetailResponse(
        **_payout_response(payout).model_dump(),
        method=PayoutMethodResponse(
            id=str(method.id),
            type=method.type,
            label=method.label,
            account_holder_name=method.account_holder_name,
            bank_name=method.bank_name,
            iban_or_account=_mask_last_four(method.iban_or_account),
            swift_code=_mask_last_four(method.swift_code),
            paypal_email=_mask_last_four(method.paypal_email),
        ),
    )


def approve_payout(
    db: Session,
    payout_id: UUID,
    payload: ApprovePayoutRequest,
    admin: AdminPrincipal,
) -> PayoutResponse:
    payout = (
        db.query(Payout).filter(Payout.id == payout_id).with_for_update().one_or_none()
    )
    if payout is None:
        raise not_found("Payout")
    if payout.status == PayoutStatus.completed:
        return _payout_response(payout)
    if payout.status != PayoutStatus.pending:
        raise conflict("Only pending payouts can be approved")

    wallet = (
        db.query(ListenerWallet)
        .filter(ListenerWallet.listener_id == payout.listener_id)
        .with_for_update()
        .one_or_none()
    )
    if wallet is None:
        raise not_found("Listener wallet")
    amount = Decimal(payout.amount)
    if Decimal(wallet.pending_balance or 0) < amount:
        raise conflict("Wallet pending balance is lower than the payout amount")

    before = {"status": payout.status.value, "reference": payout.reference}
    wallet.pending_balance = Decimal(wallet.pending_balance or 0) - amount
    payout.status = PayoutStatus.completed
    payout.reference = payload.reference
    payout.processed_at = datetime.now(timezone.utc)
    payout.reviewed_by_admin_id = admin.id
    write_audit(
        db,
        admin_user_id=admin.id,
        action="payout.approve",
        entity_type="payout",
        entity_id=payout.id,
        before=before,
        after={"status": payout.status.value, "reference": payout.reference},
    )
    db.commit()
    db.refresh(payout)
    return _payout_response(payout)


def reject_payout(
    db: Session,
    payout_id: UUID,
    payload: RejectPayoutRequest,
    admin: AdminPrincipal,
) -> PayoutResponse:
    payout = (
        db.query(Payout).filter(Payout.id == payout_id).with_for_update().one_or_none()
    )
    if payout is None:
        raise not_found("Payout")
    if payout.status == PayoutStatus.failed:
        return _payout_response(payout)
    if payout.status != PayoutStatus.pending:
        raise conflict("Only pending payouts can be rejected")

    wallet = (
        db.query(ListenerWallet)
        .filter(ListenerWallet.listener_id == payout.listener_id)
        .with_for_update()
        .one_or_none()
    )
    if wallet is None:
        raise not_found("Listener wallet")
    amount = Decimal(payout.amount)
    if Decimal(wallet.pending_balance or 0) < amount:
        raise conflict("Wallet pending balance is lower than the payout amount")

    before = {"status": payout.status.value}
    wallet.pending_balance = Decimal(wallet.pending_balance or 0) - amount
    wallet.available_balance = Decimal(wallet.available_balance or 0) + amount
    payout.status = PayoutStatus.failed
    payout.failure_reason = payload.reason
    payout.processed_at = datetime.now(timezone.utc)
    payout.reviewed_by_admin_id = admin.id
    db.add(
        WalletLedgerEntry(
            listener_id=payout.listener_id,
            type=LedgerEntryType.payout_reversal,
            amount=amount,
            balance_after=wallet.available_balance,
            payout_id=payout.id,
            idempotency_key=f"payout-reversal-{payout.id}",
            note=payload.reason,
        )
    )
    write_audit(
        db,
        admin_user_id=admin.id,
        action="payout.reject",
        entity_type="payout",
        entity_id=payout.id,
        before=before,
        after={"status": payout.status.value, "failure_reason": payload.reason},
    )
    db.commit()
    db.refresh(payout)
    return _payout_response(payout)


def get_wallet(
    db: Session,
    listener_id: UUID,
    *,
    page: int = 1,
    page_size: int = 20,
) -> WalletResponse:
    wallet = db.get(ListenerWallet, listener_id)
    if wallet is None:
        raise not_found("Listener wallet")
    page, page_size = clamp_page(page, page_size)
    query = db.query(WalletLedgerEntry).filter(
        WalletLedgerEntry.listener_id == listener_id
    )
    total = query.with_entities(func.count(WalletLedgerEntry.id)).scalar() or 0
    rows = (
        query.order_by(WalletLedgerEntry.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return WalletResponse(
        listener_id=str(listener_id),
        available_balance=Decimal(wallet.available_balance or 0),
        pending_balance=Decimal(wallet.pending_balance or 0),
        lifetime_earned=Decimal(wallet.lifetime_earned or 0),
        ledger=Paginated[WalletLedgerEntryResponse](
            items=[_ledger_response(row) for row in rows],
            total=int(total),
            page=page,
            page_size=page_size,
        ),
    )


def adjust_wallet(
    db: Session,
    listener_id: UUID,
    payload: AdjustWalletRequest,
    admin: AdminPrincipal,
) -> WalletAdjustmentResponse:
    wallet = (
        db.query(ListenerWallet)
        .filter(ListenerWallet.listener_id == listener_id)
        .with_for_update()
        .one_or_none()
    )
    if wallet is None:
        raise not_found("Listener wallet")

    # The wallet lock serializes repeated requests for the same listener, so a
    # concurrent retry sees the entry created by the first transaction.
    existing = (
        db.query(WalletLedgerEntry)
        .filter(WalletLedgerEntry.idempotency_key == payload.idempotency_key)
        .one_or_none()
    )
    if existing is not None:
        if existing.listener_id != listener_id or existing.type != LedgerEntryType.adjustment:
            raise conflict("Idempotency key is already in use")
        return WalletAdjustmentResponse(
            wallet=get_wallet(db, listener_id),
            entry=_ledger_response(existing),
        )

    amount = payload.amount.quantize(Decimal("0.01"))
    before_balance = Decimal(wallet.available_balance or 0)
    after_balance = before_balance + amount
    if after_balance < 0:
        raise validation_error("Adjustment would make the available balance negative")

    wallet.available_balance = after_balance
    entry = WalletLedgerEntry(
        listener_id=listener_id,
        type=LedgerEntryType.adjustment,
        amount=amount,
        balance_after=after_balance,
        idempotency_key=payload.idempotency_key,
        note=payload.note,
    )
    db.add(entry)
    db.flush()
    write_audit(
        db,
        admin_user_id=admin.id,
        action="wallet.adjust",
        entity_type="listener_wallet",
        entity_id=listener_id,
        before={"available_balance": str(before_balance)},
        after={
            "available_balance": str(after_balance),
            "amount": str(amount),
            "note": payload.note,
        },
    )
    db.commit()
    db.refresh(entry)
    return WalletAdjustmentResponse(
        wallet=get_wallet(db, listener_id),
        entry=_ledger_response(entry),
    )


def get_earnings_tiers(db: Session) -> EarningsTiersResponse:
    config = db.get(AppConfigKv, "earnings_tiers")
    value = config.value if config is not None else DEFAULT_EARNINGS_TIERS
    return EarningsTiersResponse(tiers=value)
