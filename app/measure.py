from dataclasses import dataclass
from typing import Optional

from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


@dataclass
class Measurement:
    type: str                       # AREA | LENGTH | NONE | UNSUPPORTED
    value: Optional[float] = None
    unit: Optional[str] = None
    projected_crs: Optional[str] = None


def utm_epsg(lon: float, lat: float) -> int:
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def measure(geom: BaseGeometry, src: CRS) -> Measurement:
    kind = geom.geom_type

    if kind in ("Point", "MultiPoint"):
        return Measurement("NONE")
    if kind not in ("Polygon", "MultiPolygon", "LineString", "MultiLineString"):
        return Measurement("UNSUPPORTED")

    # 1. find the geometry's centre in lon/lat, to pick the UTM zone
    to_lonlat = Transformer.from_crs(src, CRS.from_epsg(4326), always_xy=True)
    centre = geom.representative_point()
    lon, lat = to_lonlat.transform(centre.x, centre.y)
    epsg = utm_epsg(lon, lat)

    # 2. reproject the geometry into that UTM zone (meters)
    to_utm = Transformer.from_crs(src, CRS.from_epsg(epsg), always_xy=True)
    projected = transform(to_utm.transform, geom)

    # 3. measure
    if kind in ("Polygon", "MultiPolygon"):
        return Measurement("AREA", round(projected.area, 4), "m2", f"EPSG:{epsg}")
    return Measurement("LENGTH", round(projected.length, 4), "m", f"EPSG:{epsg}")