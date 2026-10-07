# Geospatial File Measurement API

A backend-only geospatial API built with **FastAPI** that accepts **KML files** and **Shapefile ZIP archives**, processes their features, and calculates area or length using an appropriate **UTM projected coordinate reference system (CRS)**.

The project was built as part of the **Aereo SDE internship application**.

---

## Overview

Geospatial files commonly store coordinates as latitude and longitude using a geographic CRS such as **WGS84 / EPSG:4326**.

Latitude and longitude are measured in **degrees**, so they should not be used directly for physical distance or area calculations.

This API therefore follows the workflow:

```text
Upload File
     ↓
Parse Geospatial Data
     ↓
Read Feature Geometry
     ↓
Determine Appropriate UTM Zone
     ↓
Reproject Geometry
     ↓
Calculate Area / Length
     ↓
Store Results in SQLite
     ↓
Return JSON Response
```

The API has no frontend. **FastAPI Swagger UI (`/docs`)** is used as the interactive API testing interface.

---

# Features

- Upload **KML** files
- Upload **Shapefile `.zip`** archives
- Parse geospatial features into Shapely geometries
- Detect the source CRS
- Select an appropriate UTM zone
- Reproject geometries before measurement
- Calculate polygon area in square meters
- Calculate line length in meters
- Handle point geometries without area/length measurement
- Detect unsupported geometry types
- Process features independently
- Store file and feature information in SQLite
- Retrieve uploaded file information
- Retrieve parsed features
- Retrieve calculated measurements
- Automatic API documentation through Swagger UI
- Automated tests using Pytest

---

# Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming language |
| FastAPI | REST API framework |
| Uvicorn | ASGI server |
| SQLAlchemy | Database ORM |
| SQLite | Database |
| Shapely | Geometry operations and measurements |
| PyProj | CRS handling and coordinate transformation |
| PyShp | Shapefile parsing |
| DefusedXML | Safe XML parsing |
| Pydantic | API response validation |
| Pytest | Automated testing |

---

# Project Structure

```text
geo-measure-api/
│
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── main.py
│   ├── measure.py
│   ├── models.py
│   ├── parsers.py
│   ├── schemas.py
│   └── service.py
│
├── samples/
│   ├── survey.kml
│   └── plots.zip
│
├── tests/
│   ├── __init__.py
│   └── test_api.py
│
├── .gitignore
├── requirements.txt
├── README.md
├── make_sample_shp.py
└── try_measure.py
```

---

# Architecture

```text
                        ┌──────────────────────┐
                        │      FastAPI         │
                        │      main.py         │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │    Service Layer     │
                        │      service.py      │
                        └───────┬───────┬──────┘
                                │       │
                   ┌────────────┘       └────────────┐
                   ▼                                 ▼
        ┌────────────────────┐             ┌────────────────────┐
        │      Parsers       │             │     Measurement    │
        │    parsers.py      │             │     measure.py     │
        └──────────┬─────────┘             └─────────┬──────────┘
                   │                                  │
                   └────────────────┬─────────────────┘
                                    ▼
                         ┌──────────────────────┐
                         │      Database        │
                         │ SQLite + SQLAlchemy  │
                         │   db.py / models.py  │
                         └──────────────────────┘
```

### Module Responsibilities

### `main.py`

Defines the FastAPI application and HTTP endpoints.

Responsibilities:

- Accept file uploads
- Validate file extensions
- Call the service layer
- Return API responses
- Handle HTTP errors

### `parsers.py`

Responsible for reading geospatial files.

Supported formats:

- KML
- Shapefile ZIP

The parsers convert input data into a common internal representation containing the source CRS and parsed features.

### `measure.py`

Responsible for geospatial measurement.

Responsibilities:

- Determine the appropriate UTM zone
- Create the target projected CRS
- Reproject geometries
- Calculate area or length
- Identify unsupported geometries

### `service.py`

Acts as the business-logic layer.

Responsibilities:

- Select the correct parser
- Create the file database record
- Process every feature
- Call the measurement layer
- Save results
- Handle feature-level failures
- Complete the file processing operation

### `schemas.py`

Contains Pydantic models used to define API response structures.

### `db.py`

Creates the SQLAlchemy engine and database sessions.

### `models.py`

Defines the database tables:

- `files`
- `features`

---

# Why Reprojection Is Required

A geographic CRS such as WGS84 represents positions using latitude and longitude.

For example:

```text
Longitude: 77.5946
Latitude:  12.9716
```

These values are measured in **degrees**.

A degree is an angular unit rather than a fixed physical distance. In particular, the ground distance represented by one degree of longitude changes depending on latitude.

Therefore, calculating geometry measurements directly from latitude/longitude coordinates would not provide reliable measurements in meters.

The API first converts the geometry into a projected CRS.

```text
WGS84 / EPSG:4326
        │
        │ Reprojection
        ▼
UTM Projected CRS
        │
        ▼
Area / Length
```

After reprojection:

- Length is measured in meters
- Area is measured in square meters

---

# UTM Zone Selection

UTM (Universal Transverse Mercator) divides the world into **60 zones**, with each zone covering 6 degrees of longitude.

The API selects the UTM zone based on the geographic location of the feature.

Conceptually:

```text
Longitude
    ↓
Determine UTM Zone
    ↓
Determine Hemisphere
    ↓
Create UTM CRS
    ↓
Reproject Geometry
```

For example, coordinates around Bengaluru are approximately:

```text
Longitude: 77.6
Latitude:  13.0
```

This falls within:

```text
UTM Zone: 43N
EPSG:     32643
```

The geometry is then reprojected into that CRS before measurement.

This is more appropriate for local area and distance calculations than directly measuring in EPSG:4326.

---

# Supported Geometry Types

| Geometry Type | Measurement |
|---|---|
| Point | `NONE` |
| MultiPoint | `NONE` |
| LineString | Length in meters |
| MultiLineString | Length in meters |
| Polygon | Area in square meters |
| MultiPolygon | Area in square meters |
| Unsupported geometry | `UNSUPPORTED` |

A point has no area or length measurement in the context of this API, so its measurement type is returned as:

```text
NONE
```

Unsupported geometry types are returned as:

```text
UNSUPPORTED
```

---

# Error Handling

A key design decision is that **one invalid feature should not cause the entire uploaded file to fail**.

For example, if a file contains five features:

```text
Feature 1 → OK
Feature 2 → OK
Feature 3 → ERROR
Feature 4 → OK
Feature 5 → OK
```

Feature 3 is stored with:

```text
status = ERROR
```

and its error message is recorded in the database.

The remaining features continue processing.

This is implemented by handling each feature independently inside a `try/except` block.

Unsupported geometries are also recorded without stopping the processing of the remaining features:

```text
status = UNSUPPORTED
```

This approach makes the service more resilient when processing real-world geospatial datasets.

---

# Database Design

SQLite is used as the persistence layer.

The application contains two main tables.

## `files`

Stores information about uploaded files.

Important fields:

```text
id
filename
status
crs
feature_count
error
created_at
```

Example:

```text
id:             c9f4f9afe46c44998a1f9a98bc2010a4
filename:       survey.kml
status:         COMPLETED
crs:            EPSG:4326
feature_count:  3
```

## `features`

Stores information about individual features.

Important fields:

```text
pk
file_id
index
geometry_type
geometry
properties
crs
measurement_type
value
unit
projected_crs
status
error
```

The relationship is:

```text
files
  │
  │ 1
  │
  └───────────< features
                   N
```

Each uploaded file can contain multiple feature records.

---

# Installation

## 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd geo-measure-api
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the URL of the GitHub repository.

---

## 2. Create a Virtual Environment

### Windows PowerShell

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Running the API

Start the development server:

```bash
uvicorn app.main:app --reload
```

The API will run at:

```text
http://127.0.0.1:8000
```

Interactive Swagger documentation is available at:

```text
http://127.0.0.1:8000/docs
```

The `/docs` page can be used to upload files and test the API without requiring a separate frontend.

---

# API Endpoints

## `GET /`

Returns basic API information.

Example:

```http
GET /
```

Example response:

```json
{
  "message": "Geospatial File Measurement API",
  "docs": "/docs"
}
```

---

## `POST /files`

Uploads a KML file or Shapefile ZIP.

Example:

```http
POST /files
```

Using `curl`:

```bash
curl -X POST \
  "http://127.0.0.1:8000/files" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@samples/survey.kml"
```

Example response:

```json
{
  "id": "c9f4f9afe46c44998a1f9a98bc2010a4",
  "filename": "survey.kml",
  "status": "COMPLETED",
  "crs": "EPSG:4326",
  "feature_count": 3,
  "error": null
}
```

---

## `GET /files/{file_id}`

Returns information about a previously processed file.

Example:

```http
GET /files/c9f4f9afe46c44998a1f9a98bc2010a4
```

Example response:

```json
{
  "id": "c9f4f9afe46c44998a1f9a98bc2010a4",
  "filename": "survey.kml",
  "status": "COMPLETED",
  "crs": "EPSG:4326",
  "feature_count": 3,
  "error": null
}
```

---

## `GET /files/{file_id}/features`

Returns the parsed features belonging to a file.

Example:

```http
GET /files/c9f4f9afe46c44998a1f9a98bc2010a4/features
```

Example response:

```json
[
  {
    "pk": 1,
    "file_id": "c9f4f9afe46c44998a1f9a98bc2010a4",
    "index": 0,
    "geometry_type": "Polygon",
    "measurement_type": "AREA",
    "value": 1201683.9191,
    "unit": "m2",
    "projected_crs": "EPSG:32643",
    "status": "OK",
    "error": null,
    "properties": {
      "name": "plot"
    }
  }
]
```

---

## `GET /files/{file_id}/measurements`

Returns measurement results for all features in the file.

Example:

```http
GET /files/c9f4f9afe46c44998a1f9a98bc2010a4/measurements
```

Example response:

```json
[
  {
    "feature_id": 1,
    "value": 1201683.9191,
    "unit": "m2",
    "measurement_type": "AREA",
    "projected_crs": "EPSG:32643",
    "status": "OK",
    "error": null
  },
  {
    "feature_id": 2,
    "value": 1085.6,
    "unit": "m",
    "measurement_type": "LENGTH",
    "projected_crs": "EPSG:32643",
    "status": "OK",
    "error": null
  },
  {
    "feature_id": 3,
    "value": null,
    "unit": null,
    "measurement_type": "NONE",
    "projected_crs": null,
    "status": "OK",
    "error": null
  }
]
```

---

# Sample Data

The repository contains sample files for testing:

```text
samples/
├── survey.kml
└── plots.zip
```

The sample KML contains different geometry types and can be used to verify:

- Polygon area
- LineString length
- Point handling

The Shapefile ZIP can be used to verify the ZIP-based Shapefile parser.

---

# Testing

The project uses **Pytest** for automated API testing.

Run all tests:

```bash
pytest
```

Current test coverage includes:

1. KML upload
2. Shapefile ZIP upload
3. Measurement retrieval
4. Invalid file type handling
5. Invalid KML handling
6. Unsupported geometry handling

Expected result:

```text
6 passed
```

The tests use a temporary SQLite database so that test execution does not modify the development database.

---

# Example Processing Result

For the sample KML, the API successfully processes three different feature types.

```text
Feature          Measurement       Unit       Projected CRS
----------------------------------------------------------------
Polygon          AREA              m2         EPSG:32643
LineString       LENGTH            m          EPSG:32643
Point            NONE              -          -
```

Example measured values include approximately:

```text
Area:   1,201,683.9 m2
Length: 1,085.6 m
```

---

# Design Decisions

## Why FastAPI?

FastAPI was selected because it provides:

- Simple REST API development
- Request validation
- Dependency injection
- Automatic OpenAPI schema generation
- Interactive Swagger documentation
- Good support for asynchronous file uploads

---

## Why Shapely?

Shapely provides a standard geometry model and geometry operations required by the application.

It is used for operations such as:

```python
geometry.area
geometry.length
geometry.representative_point()
```

It also allows both KML and Shapefile data to be represented using common geometry objects.

---

## Why PyProj?

PyProj is responsible for CRS and coordinate transformation operations.

It allows the application to convert coordinates from a geographic CRS such as:

```text
EPSG:4326
```

into a projected UTM CRS suitable for physical measurements.

---

## Why SQLAlchemy?

SQLAlchemy provides a clean separation between application logic and the underlying database.

The application currently uses SQLite, but the database layer can be changed later without redesigning the complete API.

---

## Why SQLite?

SQLite is lightweight and does not require a separate database server.

It is appropriate for this assignment because:

- Setup is simple
- The project is self-contained
- SQLAlchemy provides database abstraction
- It is sufficient for a small backend service

For a production geospatial application, a database such as PostgreSQL with PostGIS would be a stronger option.

---

# Learning

One of the main goals of this project was to understand the geospatial concepts instead of treating the libraries as black boxes.

## Coordinate Reference Systems

A CRS defines how coordinates represent positions on Earth.

The common geographic CRS used by KML is:

```text
WGS84 / EPSG:4326
```

Coordinates in this CRS are expressed as:

```text
longitude, latitude
```

in degrees.

---

## Geographic vs Projected CRS

A geographic CRS is useful for describing locations on the Earth.

A projected CRS converts those coordinates into a planar coordinate system.

For measurements such as:

- distance
- length
- area

a suitable projected CRS is normally preferred.

---

## UTM

UTM provides a set of local projected coordinate systems.

The world is divided into 60 UTM zones, each covering 6 degrees of longitude.

The API selects the zone corresponding to the feature location and then performs the coordinate transformation.

---

## Measuring After Reprojection

Once a polygon is transformed into a projected CRS:

```python
projected.area
```

produces an area in square meters.

For a line:

```python
projected.length
```

produces a length in meters.

This is the key geospatial idea behind the project.

---

## Feature-Level Error Handling

A real-world geospatial file may contain:

- Invalid geometries
- Missing geometry
- Unsupported geometry types
- Unexpected input data

Instead of allowing one problematic feature to stop the entire file, the application processes each feature independently.

That means valid features can still be measured even when another feature fails.

---

# Limitations

The current implementation intentionally focuses on the requirements of the assignment.

Some limitations include:

- The service is currently designed as a synchronous processing API.
- Large uploads may require background processing in a production environment.
- UTM is intended for local/regional measurements rather than global-scale analysis.
- Measurement accuracy depends on the suitability of the chosen projected CRS.
- Shapefile ZIP archives require the required Shapefile components to be present.
- The current persistence layer uses SQLite rather than a spatial database.
- Geometry validation and automatic geometry repair are limited.

---

# Future Scope

Possible improvements include:

### Database

- PostgreSQL
- PostGIS
- Spatial indexes
- Geospatial queries

### File Processing

- Background jobs
- Celery / task queues
- Progress tracking
- Large file handling
- Upload size limits

### Geospatial Support

- GeoJSON support
- GeoPackage support
- Additional CRS handling
- More robust geometry validation
- Geometry repair
- Better projection selection for larger datasets

### API

- Pagination
- Authentication
- Rate limiting
- Structured error codes
- More detailed metadata
- API versioning

### Deployment

- Docker
- CI/CD
- Automated GitHub Actions
- Production logging
- Cloud deployment

---

# Interview Talking Points

The following are the key technical decisions I would explain during an interview.

## 1. Why reproject before measuring?

Latitude and longitude are angular coordinates expressed in degrees. Physical distance and area require a projected coordinate system with suitable units. Therefore, the geometry is transformed into a projected UTM CRS before measurement.

## 2. How is the UTM zone selected?

The API determines the geographic location of the feature, obtains its longitude and latitude, and uses the longitude to determine the appropriate 6-degree UTM zone. The hemisphere is also considered when selecting the final EPSG code.

## 3. How is a bad feature handled?

Each feature is processed inside its own `try/except` block. If processing fails, that feature is stored with:

```text
status = ERROR
```

and its error message is recorded. Processing then continues with the remaining features.

## 4. Why not measure directly in EPSG:4326?

EPSG:4326 uses longitude and latitude in degrees. A degree does not represent a constant physical distance, so direct measurement would not give reliable meter-based results.

## 5. Why use UTM?

UTM provides a locally appropriate projected CRS with meter-based coordinates and generally low distortion for areas within its zone.

---

# Status Values

The API uses the following statuses.

### File Status

```text
PROCESSING
COMPLETED
FAILED
```

### Feature Status

```text
OK
UNSUPPORTED
ERROR
```

### Measurement Types

```text
AREA
LENGTH
NONE
UNSUPPORTED
```

---

# Author

**Shreyas S V**

Built as part of the Aereo SDE internship application.

---

# License

This project was created for an internship assignment and is intended primarily for evaluation and demonstration purposes.