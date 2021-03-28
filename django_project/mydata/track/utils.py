import logging
from typing import Optional, List

import gpxpy
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import GEOSGeometry


def simplify(geom: GEOSGeometry, tolerance: float = 10.0) -> GEOSGeometry:
    wgs_proj = SpatialReference("+proj=longlat +datum=WGS84")
    # TODO: determine zone number from longitude
    utm_proj = SpatialReference("+proj=utm +zone=33 +ellps=WGS84")

    # Transform to planar coordinates for better simplify operation
    ct = CoordTransform(wgs_proj, utm_proj)
    simplified_geom = geom.transform(ct, clone=True).simplify(tolerance)

    # Transform back to geographical coordinates
    ct = CoordTransform(utm_proj, wgs_proj)
    simplified_geom.transform(ct)
    return simplified_geom


def parse_gpxfile(gpx: gpxpy.gpx.GPX) -> List[gpxpy.gpx.GPXTrackPoint]:
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                logging.debug("{} ({:.6f},{:.6f}) {:.1f}m".format(p.time, p.latitude, p.longitude, p.elevation))
                points.append(p)
    return points


def read_gpxfile(fname: str) -> Optional[gpxpy.gpx.GPX]:
    """Return a GPX object using gpxpy.parse() or None if file is not a valid GPS file."""
    try:
        with open(fname, "r") as f:
            return gpxpy.parse(f)
    except (UnicodeDecodeError, gpxpy.gpx.GPXXMLSyntaxException) as err:
        logging.warning(f"Failed to parse {fname}, probably not a GPX file")
        return None
