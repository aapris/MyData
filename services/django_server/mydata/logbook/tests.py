import datetime

import pytz
from django.contrib.auth.models import User
from django.test import TestCase

from logbook.models import Message, Keyword, Record, Profile


class MessageTestCase(TestCase):
    fixtures = ['sample_keywords.json']

    def setUp(self):
        self.timezone = pytz.utc
        self.timestamp = datetime.datetime(2021, 4, 8, 12, 0).replace(tzinfo=pytz.utc)
        self.user = User.objects.create(username="test")
        Profile.objects.create(user=self.user, timezone=self.timezone)
        print(Keyword.objects.all())
        print(self.user.profile.timezone)

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
            ["lunch hernekeitto 400g", None, None, None, 0.4],
            ["drink water 2dl", None, None, 0.2, None],
        ]:
            m = Message.objects.create(text=d[0], user=self.user, time=self.timestamp)
            r: Record = m.update_record()
            self.assertEqual(r.intensity, d[1])
            self.assertEqual(r.abv, d[2])
            self.assertEqual(r.volume, d[3])
            self.assertEqual(r.quantity, d[4])

        print(m, r, r.volume)
