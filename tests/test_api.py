from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "samples"


@pytest.fixture
def client(tmp_path):
    # Use a temporary SQLite database for tests
    database_url = f"sqlite:///{tmp_path / 'test.db'}"

    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()


def test_upload_kml(client):
    file_path = SAMPLES_DIR / "survey.kml"

    with open(file_path, "rb") as file:
        response = client.post(
            "/files",
            files={
                "file": (
                    "survey.kml",
                    file,
                    "application/vnd.google-earth.kml+xml",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "survey.kml"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] == 3


def test_upload_shapefile_zip(client):
    file_path = SAMPLES_DIR / "plots.zip"

    with open(file_path, "rb") as file:
        response = client.post(
            "/files",
            files={
                "file": (
                    "plots.zip",
                    file,
                    "application/zip",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["filename"] == "plots.zip"
    assert data["status"] == "COMPLETED"
    assert data["feature_count"] > 0


def test_measurements(client):
    file_path = SAMPLES_DIR / "survey.kml"

    with open(file_path, "rb") as file:
        upload_response = client.post(
            "/files",
            files={
                "file": (
                    "survey.kml",
                    file,
                    "application/vnd.google-earth.kml+xml",
                )
            },
        )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["id"]

    response = client.get(
        f"/files/{file_id}/measurements"
    )

    assert response.status_code == 200

    measurements = response.json()

    assert len(measurements) == 3

    assert measurements[0]["measurement_type"] == "AREA"
    assert measurements[0]["unit"] == "m2"
    assert measurements[0]["status"] == "OK"

    assert measurements[1]["measurement_type"] == "LENGTH"
    assert measurements[1]["unit"] == "m"
    assert measurements[1]["status"] == "OK"

    assert measurements[2]["measurement_type"] == "NONE"
    assert measurements[2]["value"] is None


def test_invalid_file(client):
    response = client.post(
        "/files",
        files={
            "file": (
                "bad.txt",
                b"this is not a geospatial file",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_invalid_kml(client):
    response = client.post(
        "/files",
        files={
            "file": (
                "bad.kml",
                b"<not-valid-xml",
                "application/vnd.google-earth.kml+xml",
            )
        },
    )

    assert response.status_code == 400


def test_unsupported_geometry(client):
    kml = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
    <Document>
        <Placemark>
            <name>Mixed Geometry</name>
            <MultiGeometry>
                <Point>
                    <coordinates>77.5946,12.9716</coordinates>
                </Point>
                <LineString>
                    <coordinates>
                        77.5946,12.9716
                        77.6000,12.9800
                    </coordinates>
                </LineString>
            </MultiGeometry>
        </Placemark>
    </Document>
</kml>
"""

    upload_response = client.post(
        "/files",
        files={
            "file": (
                "unsupported.kml",
                kml,
                "application/vnd.google-earth.kml+xml",
            )
        },
    )

    assert upload_response.status_code == 200

    file_id = upload_response.json()["id"]

    response = client.get(
        f"/files/{file_id}/measurements"
    )

    assert response.status_code == 200

    measurements = response.json()

    assert len(measurements) == 1
    assert measurements[0]["measurement_type"] == "UNSUPPORTED"
    assert measurements[0]["status"] == "UNSUPPORTED"