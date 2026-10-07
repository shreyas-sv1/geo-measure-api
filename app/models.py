import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text

from .db import Base


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(String, primary_key=True, default=_id)
    filename = Column(String, nullable=False)
    status = Column(String, nullable=False, default="PROCESSING")  # PROCESSING | COMPLETED | FAILED
    crs = Column(String)
    feature_count = Column(Integer, default=0)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), default=_now)


class FeatureRecord(Base):
    __tablename__ = "features"

    pk = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String, ForeignKey("files.id"), index=True, nullable=False)
    index = Column(Integer, nullable=False)
    geometry_type = Column(String)
    geometry = Column(JSON)        # GeoJSON, in the file's original CRS
    properties = Column(JSON)
    crs = Column(String)
    # measurement results
    measurement_type = Column(String)   # AREA | LENGTH | NONE | UNSUPPORTED
    value = Column(Float)
    unit = Column(String)
    projected_crs = Column(String)
    status = Column(String, nullable=False, default="OK")   # OK | UNSUPPORTED | ERROR
    error = Column(Text)