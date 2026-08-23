from pydantic import BaseModel


class CatalogItemResponse(BaseModel):
    id: str
    name_en: str
    name_ar: str
    image_url: str | None = None


class ComfortAreaResponse(CatalogItemResponse):
    topic_group: str | None = None


class CatalogBundleResponse(BaseModel):
    languages: list[CatalogItemResponse]
    comfort_areas: list[ComfortAreaResponse]
    life_experiences: list[CatalogItemResponse]
    boundaries: list[CatalogItemResponse]
