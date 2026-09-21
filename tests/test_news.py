import unittest
from datetime import datetime, timedelta, timezone

from src.news import Headline, collect_headlines, parse_feed

NOW = datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc)

RSS = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0"><channel><title>t</title>
<item><title> Oil jumps as war fears grow </title><link>https://x.com/1</link><pubDate>Sat, 26 Sep 2026 10:00:00 GMT</pubDate></item>
<item><title><![CDATA[Fed keeps rates unchanged]]></title><link>https://x.com/2</link><pubDate>Fri, 25 Sep 2026 18:00:00 +0000</pubDate></item>
<item><title>Old story about oil</title><link>https://x.com/3</link><pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate></item>
<item><title>Sin fecha</title><link>https://x.com/4</link></item>
<item><title>Celebrity news</title><link>https://x.com/5</link><pubDate>Sat, 26 Sep 2026 11:00:00 GMT</pubDate></item>
</channel></rss>""".encode("utf-8")

ATOM = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Gold hits record</title><link href="https://y.com/1"/><updated>2026-09-27T09:00:00Z</updated></entry>
</feed>"""


class ParseTest(unittest.TestCase):
    def test_rss_skips_items_without_date_and_strips_titles(self):
        items = parse_feed(RSS, "Fuente")
        titles = [h.title for h in items]
        self.assertIn("Oil jumps as war fears grow", titles)
        self.assertIn("Fed keeps rates unchanged", titles)
        self.assertNotIn("Sin fecha", titles)
        self.assertTrue(all(h.published.tzinfo for h in items))

    def test_atom_entries(self):
        items = parse_feed(ATOM, "Atom")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].link, "https://y.com/1")

    def test_utf8_bom_is_accepted(self):
        self.assertEqual(len(parse_feed(b"\xef\xbb\xbf" + RSS, "BOM")), 4)


class CollectTest(unittest.TestCase):
    def cfg(self, **extra):
        cfg = {"days": 7, "max_per_feed": 5, "max_total": 10,
               "keywords": ["oil", "war", "rates", "fed"],
               "feeds": [{"name": "A", "url": "a"}]}
        cfg.update(extra)
        return cfg

    def test_filters_old_and_ranks_by_keywords(self):
        result = collect_headlines(self.cfg(), NOW, fetcher=lambda url: RSS)
        titles = [h.title for h in result]
        self.assertNotIn("Old story about oil", titles)
        self.assertEqual(titles[0], "Oil jumps as war fears grow")  # 2 palabras clave

    def test_only_keywords_and_dedupe_across_feeds(self):
        cfg = self.cfg(feeds=[{"name": "A", "url": "a", "only_keywords": True},
                              {"name": "B", "url": "b"}])
        result = collect_headlines(cfg, NOW, fetcher=lambda url: RSS)
        titles = [h.title for h in result]
        self.assertEqual(len(titles), len(set(titles)))          # sin duplicados
        self.assertEqual(sum(t == "Celebrity news" for t in titles), 1)  # solo entra por el feed B

    def test_failing_feed_is_ignored(self):
        def fetcher(url):
            if url == "bad":
                raise OSError("sin red")
            return RSS
        cfg = self.cfg(feeds=[{"name": "Malo", "url": "bad"}, {"name": "A", "url": "a"}])
        self.assertTrue(collect_headlines(cfg, NOW, fetcher=fetcher))

    def test_priority_feed_gets_bonus(self):
        cfg = self.cfg(feeds=[{"name": "A", "url": "a"}, {"name": "Oficial", "url": "atom", "priority": True}])
        fetcher = lambda url: ATOM if url == "atom" else RSS
        result = collect_headlines(cfg, NOW, fetcher=fetcher)
        self.assertEqual(result[0].source, "Oficial")


if __name__ == "__main__":
    unittest.main()
