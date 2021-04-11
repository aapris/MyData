import datetime

import pytz
from django.contrib.auth.models import User
from django.test import TestCase

from logbook.models import Message, Keyword, Record, Profile


class MessageTestCase(TestCase):
    fixtures = ["sample_keywords.json"]

    def setUp(self):
        self.timezone = "UTC"
        self.timestamp = datetime.datetime(2021, 4, 8, 12, 0).replace(tzinfo=pytz.timezone(self.timezone))
        self.user = User.objects.create(username="test")
        Profile.objects.create(user=self.user, timezone=self.timezone)
        # print(Keyword.objects.all())
        # print(f"Using timezone: {self.user.profile.timezone}")

    def test_keyword_not_found_messages(self):
        """Create Messages without valid Keyword and test that Record objects are NOT created"""
        for s in ["non existing keyword", "🧐 😮 😅 🍾", "The quick brown fox"]:
            m = Message.objects.create(text=s, user=self.user, time=self.timestamp)
            r: Record = m.update_record()
            self.assertIsNone(r)
            self.assertFalse(hasattr(m, "record"))

    def test_empty_messages(self):
        """Create empty Messages and test that Record objects are NOT created"""
        for s in ["", " ", " ", "  .  "]:
            m = Message.objects.create(text=s, user=self.user, time=self.timestamp)
            r: Record = m.update_record()
            self.assertIsNone(r)
            self.assertFalse(hasattr(m, "record"))

    def test_basic_messages(self):
        """Create Messages and test that Record objects are created properly"""
        # "keyword + other details", intensity, ABV, volume, quantity (in kilograms)
        for d in [
            ["beverage 33cl 4,7% lager", None, 4.7, 0.33, None],
            ["beverage 0.24l 13.5% red wine", None, 13.5, 0.24, None],
            ["beverage red wine 0.24l 13.5%", None, 13.5, 0.24, None],
            ["lunch hernekeitto 400g", None, None, None, 0.4],
            ["lunch 0.4kg hernekeitto", None, None, None, 0.4],
            ["water water 2dl", None, None, 0.2, None],
        ]:
            m = Message.objects.create(text=d[0], user=self.user, time=self.timestamp)
            r: Record = m.update_record()
            self.assertEqual(r.intensity, d[1])
            self.assertEqual(r.abv, d[2])
            self.assertEqual(r.volume, d[3])
            self.assertEqual(r.quantity, d[4])

    def test_time_shift_messages(self):
        """Create Messages and test that Record objects are created properly"""
        # "keyword + other details", expected timestamp
        for d in [
            ["lunch pizza margherita ****+", self.timestamp],
            ["lunch pizza -20m", self.timestamp + datetime.timedelta(minutes=-20)],
            ["lunch -20m pizza ****+", self.timestamp + datetime.timedelta(minutes=-20)],
            ["lunch pizza +20m", self.timestamp + datetime.timedelta(minutes=20)],
            ["lunch +20m pizza ****+", self.timestamp + datetime.timedelta(minutes=20)],
            ["lunch 11:00 pizza margherita", self.timestamp + datetime.timedelta(minutes=-60)],
            ["lunch 13:00 pizza margherita", self.timestamp + datetime.timedelta(minutes=60)],
            ["lunch pizza margherita +1:30", self.timestamp + datetime.timedelta(minutes=90)],
            ["lunch pizza margherita +01:30", self.timestamp + datetime.timedelta(minutes=90)],
            ["lunch pizza margherita -1:30", self.timestamp + datetime.timedelta(minutes=-90)],
            ["lunch pizza margherita -01:30", self.timestamp + datetime.timedelta(minutes=-90)],
        ]:
            m = Message.objects.create(text=d[0], user=self.user, time=self.timestamp)
            r: Record = m.update_record()
            self.assertEqual(r.time, d[1])
