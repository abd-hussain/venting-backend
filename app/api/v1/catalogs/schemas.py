from pydantic import BaseModel


class CatalogItemResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    image_url: str | None = None


class LanguageResponse(BaseModel):
    """Speaking-language catalog item (ventor + listener + speech_language)."""

    id: str
    name_en: str
    name_native: str
    name_ar: str
    flag_url: str
    flag_emoji: str | None = None
    sort_order: int


class LanguagesListResponse(BaseModel):
    items: list[LanguageResponse]


class CategoryResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    icon_emoji: str
    icon_url: str | None = None
    sort_order: int
    allows_custom_text: bool
    topic_group: str | None = None


class CategoriesListResponse(BaseModel):
    items: list[CategoryResponse]


class LifeExperienceResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    sort_order: int


class LifeExperiencesListResponse(BaseModel):
    items: list[LifeExperienceResponse]
