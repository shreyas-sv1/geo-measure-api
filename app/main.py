from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import FileRecord, FeatureRecord
from .schemas import (
    FeatureResponse,
    FileResponse,
    MeasurementResponse,
)
from .service import process_file


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Geospatial File Measurement API",
    description="Upload KML or Shapefile ZIP files and calculate feature measurements.",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Geospatial File Measurement API",
        "docs": "/docs",
    }


@app.post("/files", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    filename = file.filename.lower()

    if not (filename.endswith(".kml") or filename.endswith(".zip")):
        raise HTTPException(
            status_code=400,
            detail="Only .kml and .zip files are supported",
        )

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty",
        )

    try:
        return process_file(
            db=db,
            filename=file.filename,
            data=data,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@app.get("/files/{file_id}", response_model=FileResponse)
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
):
    file_record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id)
        .first()
    )

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return file_record


@app.get(
    "/files/{file_id}/features",
    response_model=list[FeatureResponse],
)
def get_features(
    file_id: str,
    db: Session = Depends(get_db),
):
    file_record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id)
        .first()
    )

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    features = (
        db.query(FeatureRecord)
        .filter(FeatureRecord.file_id == file_id)
        .order_by(FeatureRecord.index)
        .all()
    )

    return features


@app.get(
    "/files/{file_id}/measurements",
    response_model=list[MeasurementResponse],
)
def get_measurements(
    file_id: str,
    db: Session = Depends(get_db),
):
    file_record = (
        db.query(FileRecord)
        .filter(FileRecord.id == file_id)
        .first()
    )

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    features = (
        db.query(FeatureRecord)
        .filter(FeatureRecord.file_id == file_id)
        .order_by(FeatureRecord.index)
        .all()
    )

    return [
        MeasurementResponse(
            feature_id=feature.pk,
            value=feature.value,
            unit=feature.unit,
            measurement_type=feature.measurement_type,
            projected_crs=feature.projected_crs,
            status=feature.status,
            error=feature.error,
        )
        for feature in features
    ]