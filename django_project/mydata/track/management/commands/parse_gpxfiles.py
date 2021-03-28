import logging
from typing import Optional

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

from track.models import Trackfile, save_trackfile


def handle_file(fname: str, options: dict) -> Optional[Trackfile]:
    try:
        user = User.objects.get(username=options["username"])
    except User.DoesNotExist:
        raise CommandError("User '{}' does not exist.".format(options["username"]))
    if fname.endswith('.gpx') is False:
        logging.warning(f"{fname} not processed (doesn't have .gpx filename extension)")
        return
    try:
        trackfile = save_trackfile(fname, user, options["override"])
        if trackfile:
            trackfile.parse_trackfile()
            return trackfile
    except IntegrityError as err:
        logging.error(f"{err}")
        raise


class Command(BaseCommand):
    help = "Parse GPS track files and save tracks into the database"

    def add_arguments(self, parser):
        parser.add_argument("files", nargs="+", type=str)
        parser.add_argument("-u", "--username", required=True)
        parser.add_argument("-o", "--override", action="store_true", help="Delete previously saved identical file")
        parser.add_argument(
            "--log",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="ERROR",
            help="Set the logging level",
        )

    def handle(self, *args, **options):
        logging.basicConfig(
            format="%(asctime)s %(levelname)-8s %(message)s",
            level=getattr(logging, options["log"]),
        )
        success = ignore = 0
        for fname in options["files"]:
            trackfile = handle_file(fname, options)
            if trackfile:
                logging.info(
                    "Saved {}: {} trackpoints, {} simplified trackpoints".format(
                        trackfile.filename, trackfile.trackpoint_cnt, trackfile.geometry.num_points
                    )
                )
                success += 1
            else:
                logging.info(f"Ignored {fname}")
                ignore += 1
        self.stdout.write(self.style.SUCCESS(f"Saved {success} and ignored {ignore} track files"))
