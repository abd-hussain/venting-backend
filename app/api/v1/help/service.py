from sqlalchemy.orm import Session

from app.api.v1.help.schemas import HelpDocumentLink, HelpLinksResponse
from app.core.errors import help_documents_unavailable, invalid_help_locale
from app.models.help import HelpDocument

SUPPORTED_LOCALES = frozenset({"en", "ar"})
FALLBACK_LOCALE = "en"


def resolve_locale(raw: str | None, *, strict: bool = False) -> str:
    if raw is None or not raw.strip():
        return FALLBACK_LOCALE
    primary = raw.strip().lower().replace("_", "-").split(",")[0].split("-")[0]
    if primary in SUPPORTED_LOCALES:
        return primary
    if strict:
        raise invalid_help_locale()
    return FALLBACK_LOCALE


def _link(row: HelpDocument) -> HelpDocumentLink:
    return HelpDocumentLink(
        topic=row.topic,
        locale=row.locale,
        title=row.title,
        url=row.url,
        updated_at=row.updated_at,
    )


def get_help_links(
    db: Session,
    *,
    locale: str | None,
    locale_from_query: bool,
    topic: str | None = None,
) -> HelpLinksResponse:
    resolved = resolve_locale(locale, strict=locale_from_query)
    query = db.query(HelpDocument).filter(HelpDocument.is_published.is_(True))
    if topic is not None and topic.strip():
        query = query.filter(HelpDocument.topic == topic.strip().lower())
    published = query.all()
    if not published:
        raise help_documents_unavailable()

    by_topic: dict[str, dict[str, HelpDocument]] = {}
    for row in published:
        by_topic.setdefault(row.topic, {})[row.locale] = row

    items: list[HelpDocumentLink] = []
    for topic_key in sorted(by_topic.keys()):
        locales = by_topic[topic_key]
        row = locales.get(resolved) or locales.get(FALLBACK_LOCALE)
        if row is not None:
            items.append(_link(row))

    if not items:
        raise help_documents_unavailable()

    return HelpLinksResponse(locale=resolved, items=items)
