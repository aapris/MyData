import gzip
import hashlib
import io
import os
from typing import List, Optional

import gpxpy
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point, LineString, MultiLineString
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.template.defaultfilters import slugify

from track.utils import simplify, parse_gpxfile

trackfile_storage = FileSystemStorage(location=settings.TRACK.get("FILE_DIR"))

TIMEFORMAT = "%Y-%m-%dT%H:%M:%S%Z"


def get_trackfile_upload_to(obj, filename):
    """
    Return the path where the original file will be saved.
    Files are split into a directory hierarchy, which bases on object's id,
    e.g. if obj.id is 12345, fill path will be 000/012/filename
    so there will be max 1000 files in a directory.
    """
    if obj.id is None:
        obj.save()  # save the object to ensure there is obj.id available
    longid = "{:09d}".format(obj.id)  # e.g. '000012345'
    chunkindex = [i for i in range(0, len(longid) - 3, 3)]  # -> [0, 3, 6]
    path = os.sep.join([longid[j: j + 3] for j in chunkindex] + [filename])
    return path


class Tracksource(models.Model):
    name = models.CharField(max_length=256, editable=True)
    slug = models.SlugField(max_length=64, editable=True)
    description = models.TextField(blank=True)


class Trackfile(models.Model):
    tracksource = models.ForeignKey(
        Tracksource, db_index=True, blank=True, null=True, editable=False, on_delete=models.CASCADE
    )
    user = models.ForeignKey(User, db_index=True, editable=False, on_delete=models.CASCADE)
    # Original base filename in file system or the name of uploaded file
    filename = models.CharField(max_length=256, blank=True, editable=False)
    # Size of original data in bytes
    filesize = models.IntegerField(editable=False)
    # Saved file's compression type (None, gzip)
    compression = models.CharField(max_length=10, blank=True, editable=False)
    # Original data saved in the file system
    file = models.FileField(storage=trackfile_storage, upload_to=get_trackfile_upload_to, editable=False)
    # The type of original data (GPX_FILE, CUSTOM_JSON_FILE, HTTP_POST_TRACKPOINTS)
    datatype = models.CharField(max_length=32, blank=True, editable=False)
    # SHA1 hash of original data in hex-format
    sha1 = models.CharField(max_length=40, db_index=True, editable=False)
    # First and last trackpoint's timestamps found from this set of trackpoints
    starttime = models.DateTimeField(blank=True, null=True, db_index=True, editable=False)
    endtime = models.DateTimeField(blank=True, null=True, db_index=True, editable=False)
    # Total number of valid and unique trackpoints found
    trackpoint_cnt = models.IntegerField(blank=True, null=True)
    geometry = models.MultiLineStringField(geography=True, blank=True, null=True, db_index=True, editable=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Make sure that every user has a file only once
        unique_together = ("user", "sha1")

    def set_trackpoint_fields(self):
        """Precalculated values for trackpoint count and first/last timestamps."""
        trackpoints = self.trackpoints.order_by("time")
        self.trackpoint_cnt = trackpoints.count()
        if self.trackpoint_cnt > 0:
            self.starttime = trackpoints[0].time
            self.endtime = trackpoints[self.trackpoint_cnt - 1].time
        self.save()

    def set_file(self, originalfilename: str, filecontent, override=False):
        """
        Set Trackpoint.file and all it's related fields.
        filecontent may be
        - open file handle (opened in "rb"-mode)
        - existing file name (full path)
        NOTE: this reads all file content into memory
        """
        if hasattr(filecontent, "read"):
            filecontent.seek(0)
            filedata = filecontent.read()
            filecontent.close()
        elif len(filecontent) < 1000 and os.path.isfile(filecontent):
            with open(filecontent, "rb") as f:
                filedata = f.read()
        else:
            raise ValueError(f"Expecting a file handle or path to existing file, got {filecontent}")
        if originalfilename:
            self.filename = os.path.basename(originalfilename)
        else:  # Dummy name for nameless data (e.g. AJAX POSTs)
            self.filename = "http.post"
        root, ext = os.path.splitext(self.filename)
        self.filesize = len(filedata)
        self.sha1 = hashlib.sha1(filedata).hexdigest()
        exists = Trackfile.objects.filter(sha1=self.sha1)
        if exists.count() > 0:
            if override:
                exists.delete()
            else:
                return False
        self.save()
        filename = "{:09}-{}{}.gz".format(self.id, slugify(root), ext.lower())
        # Compress filedata to preserve disk space
        file_out = io.BytesIO()
        gzipper = gzip.GzipFile(fileobj=file_out, mode="wb")
        gzipper.write(filedata)
        gzipper.flush()
        gzipper.close()
        file_out.flush()
        self.file.save(filename, ContentFile(file_out.getvalue()))
        self.compression = "gzip"
        self.save()
        return True

    def generate_tracksegments(self):
        """
        Deletes old Trackseg objects between given range from the database.
        Loops all trackpoints between given range and creates Tracksegs for them.
        """
        # First delete all Tracksegments of this Trackfile
        self.tracksegs.all().delete()
        # Then recreate
        trackpoints = self.trackpoints.order_by("time")
        points = []
        tracksegs = []
        # TODO: configurable options
        maxtime = 120  # seconds
        limit = 1000
        for tp in trackpoints:  # Loop all Trackpoints (max 'limit')
            timediff = (tp.time - points[-1].time).seconds if points else 0  # Seconds between 2 last points
            if timediff > maxtime or len(points) >= limit:
                trackseg = trackpointlist_to_trackseg(self, points)  # Create new Trackseg
                tracksegs.append(trackseg)
                # if track was split because of limit then reuse the last point
                if len(points) >= limit:
                    points = [points[-1]]
                else:
                    points = []
            points.append(tp)
        trackseg = trackpointlist_to_trackseg(self, points)  # Create last new Trackseg
        tracksegs.append(trackseg)
        simplified_linestrings = []
        for trackseg in tracksegs:
            simplified_linestrings.append(simplify(trackseg.geometry, 30))
        self.geometry = MultiLineString(simplified_linestrings)
        self.save()

    def parse_trackfile(self):
        """
        Parse GPX file, create Trackpoints for all trackpoints found in it,
        set start and end times and finally generate track segment objects
        related to this Trackfile.
        """
        with transaction.atomic():
            with self.get_file_handle() as f:
                gpx = gpxpy.parse(f)
            points = parse_gpxfile(gpx)
            if points is None:
                return None
            save_trackpoints(points, self)
            self.set_trackpoint_fields()
            self.generate_tracksegments()

    def get_file_handle(self):
        """
        Return open filehandle for original file.
        After reading file data this handle must be properly closed.
        """
        if self.compression == "gzip":
            f = gzip.open(self.file.path, "rb")
        else:
            f = open(self.file.path, "rb")
        return f

    def get_file_content(self):
        """Return original uncompressed file data."""
        with self.get_file_handle() as f:
            return f.read()

    def __str__(self):
        st = self.starttime.strftime(TIMEFORMAT) if self.starttime else ""
        return '"{}" ({})'.format(self.filename, st)


@receiver(post_delete, sender=Trackfile)
def submission_delete(sender, instance, **kwargs):
    """Add .deleted postfix to files related to deleted Trackfile records"""
    os.rename(instance.file.path, f"{instance.file.path}.deleted")


class Trackpoint(models.Model):
    """
    Contains all gathered data of single GPS measurement.
    Fields follow mostly elements in GPX standard's <trkpt> element.
    """

    user = models.ForeignKey(User, db_index=True, blank=True, null=True, on_delete=models.CASCADE)
    trackfile = models.ForeignKey(
        Trackfile, db_index=True, blank=True, null=True, on_delete=models.CASCADE, related_name="trackpoints"
    )
    status = models.IntegerField(default=1)
    time = models.DateTimeField(db_index=True)  # See ./sql/Trackpoint.sql
    # For convenience, lat and lon in numeric form too
    lat = models.FloatField()  # degrees (°) -90.0 - 90.0
    lon = models.FloatField()  # degrees (°) -180.0 - 180.0
    speed = models.FloatField(blank=True, null=True)  # meters per second (m/s)
    course = models.FloatField(blank=True, null=True)  # degrees (°) 0.0 - 360.0
    ele = models.FloatField(blank=True, null=True)  # meters (m)
    # Horizontal and Vertical accuracy (pre-calculated by some GPS chips or software)
    hacc = models.FloatField(blank=True, null=True)
    vacc = models.FloatField(blank=True, null=True)
    # See Dilution of precision at
    # http://en.wikipedia.org/wiki/Dilution_of_precision_%28GPS%29
    hdop = models.FloatField(blank=True, null=True)  # horizontal
    vdop = models.FloatField(blank=True, null=True)  # vertical
    pdop = models.FloatField(blank=True, null=True)  # positional (3D)
    tdop = models.FloatField(blank=True, null=True)  # time
    # Satellites in view and used
    sat = models.IntegerField(blank=True, null=True)
    satavail = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    # See https://postgis.net/docs/using_postgis_dbmanagement.html#PostGIS_GeographyVSGeometry
    # point_geometry = models.PointField(editable=True)
    geometry = models.PointField(geography=True, db_index=True, editable=True)

    def __str__(self):
        return "{} {},{},{}".format(self.pk, self.lat, self.lon, self.time.strftime(TIMEFORMAT))

    def set_data(self, data):
        """
        'data' must contain always lat & lon keys and time,
        if time is not already defined.
        """
        try:
            self.lat = data["lat"]
            self.lon = data["lon"]
            self.geometry = Point(data["lon"], data["lat"])
            if self.time is None and "time" in data:
                self.time = data["time"]
        except:
            return False
        # Optional fields, based of fields which have been seen in various GPS sources
        for field in ["ele", "speed", "course", "hacc", "vacc", "hdop", "vdop", "pdop", "tdop", "sat", "satavail"]:
            self.__setattr__(field, data.get(field))
        return True


class Trackseg(models.Model):
    """
    Trackseg is a combination of continuous set of Trackpoints (Linestring)
    without any other information than coordinates.
    This is used to visualize (faster than rendering single Trackpoints)
    tracks on the map.
    """

    user = models.ForeignKey(User, db_index=True, blank=True, null=True, editable=False, on_delete=models.CASCADE)
    trackfile = models.ForeignKey(
        Trackfile, db_index=True, blank=True, null=True, on_delete=models.CASCADE, related_name="tracksegs"
    )
    level = models.IntegerField(default=0)  # 0 contains all trackpoints
    length = models.FloatField(default=0)  # meters
    trackpoint_cnt = models.IntegerField()
    starttime = models.DateTimeField(db_index=True, editable=False)
    endtime = models.DateTimeField(db_index=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    geometry = models.LineStringField(geography=True, db_index=True, editable=True)

    @property
    def length_km(self):
        """Return Trackseg's length in kilometers."""
        return round((self.length / 1000.0), 2)

    def __str__(self):
        return "{} ({} pnts, {} km)".format(self.starttime.strftime(TIMEFORMAT), self.trackpoint_cnt, self.length_km)


def save_trackpoints(points: List[gpxpy.gpx.GPXTrackPoint], trackfile: Trackfile) -> List[Trackpoint]:
    tpoints = []
    for pnt in points:
        tp = {
            "time": pnt.time,
            "lat": pnt.latitude,
            "lon": pnt.longitude,
            "ele": pnt.elevation,
            "hdop": pnt.horizontal_dilution,
            "vdop": pnt.vertical_dilution,
            "speed": pnt.speed,
            "course": pnt.course,
            "sat": pnt.satellites,
        }
        p = Trackpoint(**tp)
        p.trackfile = trackfile
        p.user = trackfile.user
        p.geometry = Point(pnt.longitude, pnt.latitude)
        tpoints.append(p)
    return Trackpoint.objects.bulk_create(tpoints)


def save_trackfile(fname: str, user: User, override=False) -> Optional[Trackfile]:
    trackfile = Trackfile(user=user)
    saved = trackfile.set_file(fname, fname, override=override)
    if saved is False:
        return None
    else:
        return trackfile


def trackpointlist_to_trackseg(trackfile, points):
    if len(points) == 1:  # Add single point twice, LineString can't have only 1 point
        points.append(points[0])
    trackseg = Trackseg(trackfile=trackfile, user=trackfile.user)
    points_geo = [x.geometry for x in points]
    if len(points_geo) == 0:
        return 0
    trackseg.geometry = LineString(points_geo)
    trackseg.starttime = points[0].time
    trackseg.endtime = points[-1].time
    trackseg.trackpoint_cnt = len(points)
    # Transform into projected coordinate system (using web mercator) to get length in meters
    # TODO: make sure this is correct and accurate way to do it
    trackseg_web_mercator = LineString(points_geo, srid=4326)
    trackseg_web_mercator.transform(3857)
    trackseg.length = trackseg_web_mercator.length
    trackseg.save()
    return trackseg
