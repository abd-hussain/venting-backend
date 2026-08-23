from pydantic import BaseModel, Field


class CatalogItemResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    is_active: bool
    image_url: str | None = None


class ComfortAreaResponse(CatalogItemResponse):
    topic_group: str | None = None


class CatalogUpsertRequest(BaseModel):
    name_en: str = Field(min_length=1, max_length=120)
    name_ar: str = Field(min_length=1, max_length=120)
    is_active: bool = True


class ComfortAreaUpsertRequest(CatalogUpsertRequest):
    topic_group: str | None = Field(default=None, max_length=64)
