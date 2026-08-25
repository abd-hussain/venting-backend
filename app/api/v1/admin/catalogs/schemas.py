from pydantic import BaseModel, Field


class CatalogItemResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    is_active: bool
    image_url: str | None = None


class LanguageResponse(BaseModel):
    id: str
    name_en: str
    name_native: str
    name_ar: str
    flag_url: str | None = None
    flag_emoji: str | None = None
    sort_order: int = 0
    is_active: bool


class ComfortAreaResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    icon_emoji: str = "📌"
    icon_url: str | None = None
    sort_order: int = 0
    allows_custom_text: bool = False
    audience: str = "all"
    topic_group: str | None = None
    is_active: bool


class CatalogUpsertRequest(BaseModel):
    name_en: str = Field(min_length=1, max_length=120)
    name_ar: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class LanguageUpsertRequest(CatalogUpsertRequest):
    name_native: str = Field(min_length=1, max_length=64)
    flag_emoji: str | None = Field(default=None, max_length=16)
    sort_order: int = Field(default=0, ge=0)


class ComfortAreaUpsertRequest(CatalogUpsertRequest):
    topic_group: str | None = Field(default=None, max_length=64)
    icon_emoji: str = Field(default="📌", min_length=1, max_length=16)
    sort_order: int = Field(default=0, ge=0)
    allows_custom_text: bool = False
    audience: str = Field(default="all", min_length=1, max_length=32)
