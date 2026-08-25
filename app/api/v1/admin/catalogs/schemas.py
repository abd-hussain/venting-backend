from pydantic import BaseModel, Field


class CatalogItemResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    is_active: bool
    image_url: str | None = None
    sort_order: int | None = None


class ComfortAreaResponse(CatalogItemResponse):
    topic_group: str | None = None
    icon_key: str = "category"
    sort_order: int = 0
    allows_custom_text: bool = False
    audience: str = "all"


class CatalogUpsertRequest(BaseModel):
    name_en: str = Field(min_length=1, max_length=120)
    name_ar: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class LanguageUpsertRequest(CatalogUpsertRequest):
    sort_order: int = Field(default=0, ge=0)


class ComfortAreaUpsertRequest(CatalogUpsertRequest):
    topic_group: str | None = Field(default=None, max_length=64)
    icon_key: str = Field(default="category", min_length=1, max_length=64)
    sort_order: int = Field(default=0, ge=0)
    allows_custom_text: bool = False
    audience: str = Field(default="all", min_length=1, max_length=32)
