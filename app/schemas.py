from typing import Any

from pydantic import BaseModel


class FeatureResponse(BaseModel):
    pk: int
    file_id: str
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
    id: str
    filename: str
    status: str
    crs: str | None
    feature_count: int
    error: str | None


class MeasurementResponse(BaseModel):
    feature_id: int
    value: float | None
    unit: str | None
    measurement_type: str | None
    projected_crs: str | None
    status: str
    error: str | None