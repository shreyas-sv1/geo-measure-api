from pydantic import BaseModel
from typing import Any


class FeatureResponse(BaseModel):
    id: int
    index: int
    geometry_type: str | None
    measurement_type: str | None
    value: float | None
    unit: str | None
    projected_crs: str | None
    status: str
    error: str | None
    properties: dict[str, Any] | None


class FileResponse(BaseModel):
    id: int
    filename: str
    status: str
    crs: str
    feature_count: int


class MeasurementResponse(BaseModel):
    feature_id: int
    value: float | None
    unit: str | None
    measurement_type: str | None
    projected_crs: str | None
    status: str
    error: str | None