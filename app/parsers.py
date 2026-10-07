from dataclasses import dataclass, field
from typing import Optional

from defusedxml import ElementTree as ET
from pyproj import CRS
from shapely.geometry import (
    GeometryCollection, LineString, MultiLineString, MultiPoint,
    MultiPolygon, Point, Polygon,
)
from shapely.geometry.base import BaseGeometry

GEOM_TAGS = ("Point", "LineString", "Polygon", "MultiGeometry")


class ParseError(ValueError):
    """The uploaded file could not be understood."""


@dataclass
class ParsedFeature:
    index: int
    geometry: Optional[BaseGeometry]
    properties: dict = field(default_factory=dict)


@dataclass
class ParsedFile:
    crs: CRS
    features: list


def _local(tag: str) -> str:
    # "{http://www.opengis.net/kml/2.2}Polygon" -> "Polygon"
    return tag.rsplit("}", 1)[-1]


def _child(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _coords(el) -> list:
    node = _child(el, "coordinates")
    if node is None or not (node.text or "").strip():
        raise ParseError("Geometry has no coordinates")
    points = []
    for token in node.text.split():
        parts = token.split(",")
        points.append((float(parts[0]), float(parts[1])))  # lon, lat
    return points


def _geometry(el) -> BaseGeometry:
    kind = _local(el.tag)
    if kind == "Point":
        return Point(_coords(el)[0])
    if kind == "LineString":
        return LineString(_coords(el))
    if kind == "Polygon":
        outer = _child(el, "outerBoundaryIs")
        shell = _coords(_child(outer, "LinearRing"))
        holes = [
            _coords(_child(c, "LinearRing"))
            for c in el
            if _local(c.tag) == "innerBoundaryIs"
        ]
        return Polygon(shell, holes)
    if kind == "MultiGeometry":
        parts = [_geometry(c) for c in el if _local(c.tag) in GEOM_TAGS]
        types = {type(p) for p in parts}
        if types == {Polygon}:
            return MultiPolygon(parts)
        if types == {LineString}:
            return MultiLineString(parts)
        if types == {Point}:
            return MultiPoint(parts)
        return GeometryCollection(parts)
    raise ParseError(f"Unsupported geometry: {kind}")


def parse_kml(data: bytes) -> ParsedFile:
    try:
        root = ET.fromstring(data)
    except Exception as exc:
        raise ParseError(f"Invalid KML/XML: {exc}") from exc

    features = []
    placemarks = [e for e in root.iter() if _local(e.tag) == "Placemark"]
    for i, pm in enumerate(placemarks):
        props = {}
        name = _child(pm, "name")
        if name is not None and name.text:
            props["name"] = name.text.strip()

        geom = None
        geom_el = next((c for c in pm if _local(c.tag) in GEOM_TAGS), None)
        if geom_el is not None:
            try:
                geom = _geometry(geom_el)
            except ValueError as exc:  # one bad placemark must not fail the file
                props["_parse_error"] = str(exc)
        features.append(ParsedFeature(i, geom, props))

    return ParsedFile(CRS.from_epsg(4326), features)  # KML is always WGS84