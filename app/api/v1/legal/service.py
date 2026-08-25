from sqlalchemy.orm import Session

from app.api.v1.legal.schemas import LegalDocumentLink, LegalLinksResponse
from app.core.errors import invalid_legal_locale, legal_documents_unavailable
from app.models.legal import LegalDocument

SUPPORTED_LOCALES = frozenset({"en", "ar"})
FALLBACK_LOCALE = "en"
DOCUMENTS = ("terms", "privacy")


def resolve_locale(raw: str | None, *, strict: bool = False) -> str:
    if raw is None or not raw.strip():
        return FALLBACK_LOCALE
    primary = raw.strip().lower().replace("_", "-").split(",")[0].split("-")[0]
    if primary in SUPPORTED_LOCALES:
        return primary
    if strict:
        raise invalid_legal_locale()
    return FALLBACK_LOCALE


def _link(row: LegalDocument) -> LegalDocumentLink:
    return LegalDocumentLink(
        document=row.document,
        locale=row.locale,
        title=row.title,
        url=row.url,
        updated_at=row.updated_at,
    )


def _pick(
    rows: dict[tuple[str, str], LegalDocument],
    document: str,
    preferred: str,
) -> LegalDocument | None:
    row = rows.get((document, preferred))
    if row is not None:
        return row
    if preferred != FALLBACK_LOCALE:
        return rows.get((document, FALLBACK_LOCALE))
    return None


def get_legal_links(
    db: Session,
    *,
    locale: str | None,
    locale_from_query: bool,
) -> LegalLinksResponse:
    resolved = resolve_locale(locale, strict=locale_from_query)
    published = (
        db.query(LegalDocument)
        .filter(LegalDocument.is_published.is_(True))
        .all()
    )
    by_key = {(row.document, row.locale): row for row in published}

    terms = _pick(by_key, "terms", resolved)
    privacy = _pick(by_key, "privacy", resolved)
    if terms is None or privacy is None:
        raise legal_documents_unavailable()

    return LegalLinksResponse(
        locale=resolved,
        terms=_link(terms),
        privacy=_link(privacy),
    )
