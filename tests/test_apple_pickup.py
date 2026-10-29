import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "i-want-an-iphone-right-now", "scripts"))
import apple_pickup as ap  # noqa: E402


def store(num, name, city, dist, avail):
    return {"storeNumber": num, "storeName": name, "city": city, "storeDistanceWithUnit": dist,
            "partsAvailability": {part: {"pickupDisplay": "available" if ok else "unavailable"}
                                  for part, ok in avail.items()}}


class ParseArgsTest(unittest.TestCase):
    def test_requires_zip_or_region(self):
        with self.assertRaises(SystemExit):
            ap.parse_args([])

    def test_zip_and_region_are_exclusive(self):
        with self.assertRaises(SystemExit):
            ap.parse_args(["--zip", "94108", "--region", "bay-area"])

    def test_rejects_empty_zip(self):
        for z in ["", " , "]:
            with self.assertRaises(SystemExit):
                ap.parse_args(["--zip", z])

    def test_rejects_unknown_config(self):
        with self.assertRaises(SystemExit):
            ap.parse_args(["--zip", "94108", "--configs", "3tb-gold"])

    def test_defaults(self):
        args = ap.parse_args(["--zip", "94108, 95014"])
        configs, zips, expected, area = ap.plan(args)
        self.assertEqual(args.carrier, "unlocked")
        self.assertEqual(len(configs), 8)
        self.assertEqual(zips, ["94108", "95014"])
        self.assertIsNone(expected)
        self.assertEqual(area, "stores nearest 94108, 95014")

    def test_stores_filter(self):
        args = ap.parse_args(["--zip", "10002", "--stores", "r032, R654,"])
        _, zips, expected, area = ap.plan(args)
        self.assertEqual(zips, ["10002"])
        self.assertEqual(list(expected), ["R032", "R654"])
        self.assertEqual(area, "selected stores near 10002")

    def test_stores_needs_zip_and_a_store(self):
        for argv in (["--region", "bay-area", "--stores", "R075"], ["--zip", "10002", "--stores", " , "]):
            with self.assertRaises(SystemExit):
                ap.parse_args(argv)

    def test_email_needs_api_key(self):
        old = os.environ.pop("RESEND_API_KEY", None)
        try:
            with self.assertRaises(SystemExit):
                ap.parse_args(["--zip", "94108", "--email", "a@example.com"])
        finally:
            if old is not None:
                os.environ["RESEND_API_KEY"] = old


class ReportTest(unittest.TestCase):
    configs = [ap.CONFIGS["1tb-night"], ap.CONFIGS["2tb-night"]]
    one, two = configs[0][0], configs[1][0]

    def responses(self):
        return [
            (self.one, [store("R075", "Union Square", "San Francisco", "0.1 mi", {self.one: False}),
                        store("R217", "Chestnut Street", "San Francisco", "2 mi", {self.one: True})]),
            (self.two, [store("R075", "Union Square", "San Francisco", "0.1 mi", {self.two: False}),
                        store("R217", "Chestnut Street", "San Francisco", "2 mi", {self.two: False})]),
        ]

    def test_zip_report_lists_every_store_and_hits(self):
        stores, avail = ap.merge(self.responses(), self.configs)
        hits, text = ap.availability_report(stores, avail, None, self.configs, "att", "stores nearest 94108")
        self.assertEqual(hits, ["1TB Night Sky at Chestnut Street, San Francisco"])
        self.assertIn("R075 Union Square, San Francisco (0.1 mi)", text)
        self.assertIn("AVAILABLE", text)
        self.assertIn("Checked 2 of 2 stores nearest 94108 x 2 configs.", text)
        self.assertTrue(ap.subject(hits, 2, 2).startswith("IN STOCK: "))

    def test_region_report_flags_missing_and_ignores_others(self):
        stores, avail = ap.merge(self.responses(), self.configs)
        expected = {"R075": "Union Square", "R033": "Stonestown"}
        hits, text = ap.availability_report(stores, avail, expected, self.configs, "att", "bay-area stores")
        self.assertEqual(hits, [])
        self.assertIn("R033 Stonestown", text)
        self.assertIn("MISSING", text)
        self.assertNotIn("Chestnut", text)
        self.assertIn("Available: none", text)
        self.assertEqual(ap.subject(hits, 2, 2), "No stock: iPhone Duo pickup (2 stores x 2 configs)")

    def test_selected_stores_report_keeps_names_and_flags_missing(self):
        stores, avail = ap.merge(self.responses(), self.configs)
        expected = {"R217": "", "R032": ""}
        hits, text = ap.availability_report(stores, avail, expected, self.configs, "att", "selected stores near 94108")
        self.assertEqual(hits, ["1TB Night Sky at Chestnut Street, San Francisco"])
        self.assertIn("R217 Chestnut Street, San Francisco", text)
        self.assertIn("R032                ", text)
        self.assertIn("MISSING", text)
        self.assertNotIn("Union Square", text)

    def test_store_list(self):
        stores, _ = ap.merge(self.responses()[:1], self.configs)
        text = ap.store_list_report(stores, None, "stores nearest 94108")
        self.assertTrue(text.startswith("2 stores nearest 94108:"))


if __name__ == "__main__":
    unittest.main()


class FakePage:
    def __init__(self, replies):
        self.replies, self.calls, self.reloads = list(replies), 0, 0

    async def evaluate(self, js, url):
        self.calls += 1
        return self.replies.pop(0) if self.replies else [541, "<html>Page Not Found</html>"]

    async def reload(self, **kw):
        self.reloads += 1

    async def wait_for_timeout(self, ms):
        pass


class FetchJsonTest(unittest.TestCase):
    def test_retries_past_bot_shield(self):
        page = FakePage([[541, "<html>"], [541, "<html>"], [200, '{"ok": 1}']])
        self.assertEqual(ap.asyncio.run(ap.fetch_json(page, "/u", "x")), {"ok": 1})
        self.assertEqual(page.calls, 3)

    def test_gives_up_after_attempts_with_one_reload(self):
        page = FakePage([])
        with self.assertRaisesRegex(RuntimeError, "HTTP 541"):
            ap.asyncio.run(ap.fetch_json(page, "/u", "x", attempts=4))
        self.assertEqual((page.calls, page.reloads), (4, 1))
