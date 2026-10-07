from sqlalchemy.orm import Session

from .models import FileRecord, FeatureRecord
from .parsers import parse_kml, parse_shapefile_zip, ParseError
from .measure import measure


def process_file(
    db: Session,
    filename: str,
    data: bytes,
):
    # Choose the correct parser
    if filename.lower().endswith(".kml"):
        parsed = parse_kml(data)

    elif filename.lower().endswith(".zip"):
        parsed = parse_shapefile_zip(data)

    else:
        raise ParseError("Only .kml and .zip files are supported")

    # Create file record
    file_record = FileRecord(
        filename=filename,
        status="PROCESSING",
        crs=parsed.crs.to_string(),
        feature_count=0,
    )

    db.add(file_record)
    db.flush()

    # Process each feature independently
    for feature in parsed.features:

        feature_record = FeatureRecord(
            file_id=file_record.id,
            index=feature.index,
            properties=feature.properties,
            crs=parsed.crs.to_string(),
        )

        try:
            # Check if geometry exists
            if feature.geometry is None:
                feature_record.status = "ERROR"
                feature_record.error = "Feature has no geometry"

            else:
                feature_record.geometry_type = feature.geometry.geom_type

                # Measure the feature
                result = measure(
                    feature.geometry,
                    parsed.crs
                )

                feature_record.measurement_type = result.type
                feature_record.value = result.value
                feature_record.unit = result.unit
                feature_record.projected_crs = result.projected_crs

                # Handle supported and unsupported geometries
                if result.type == "UNSUPPORTED":
                    feature_record.status = "UNSUPPORTED"
                    feature_record.error = "Geometry type is not supported"
                else:
                    feature_record.status = "OK"

        except Exception as exc:
            # One bad feature should not stop the entire file
            feature_record.status = "ERROR"
            feature_record.error = str(exc)

        db.add(feature_record)

    # File processing completed
    file_record.status = "COMPLETED"
    file_record.feature_count = len(parsed.features)

    db.commit()
    db.refresh(file_record)

    return file_record