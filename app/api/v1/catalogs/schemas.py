from pydantic import BaseModel


class CatalogItemResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    image_url: str | None = None
    sort_order: int | None = None


class LanguageResponse(BaseModel):
    """Speaking-language catalog item (listener languages + session speech_language)."""

    id: str
    name_en: str
    name_ar: str
    sort_order: int
    image_url: str | None = None


class LanguagesListResponse(BaseModel):
    items: list[LanguageResponse]


class ComfortAreaResponse(CatalogItemResponse):
    topic_group: str | None = None
    icon_key: str | None = None
    sort_order: int | None = None
    allows_custom_text: bool | None = None
    audience: str | None = None


class CategoryResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    icon_key: str
    sort_order: int
    allows_custom_text: bool
    topic_group: str | None = None


class CategoriesListResponse(BaseModel):
    items: list[CategoryResponse]


class CatalogBundleResponse(BaseModel):
    languages: list[LanguageResponse]
    comfort_areas: list[ComfortAreaResponse]
    life_experiences: list[CatalogItemResponse]
    boundaries: list[CatalogItemResponse]
