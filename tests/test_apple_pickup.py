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

    def test_store_list(self):
        stores, _ = ap.merge(self.responses()[:1], self.configs)
        text = ap.store_list_report(stores, None, "stores nearest 94108")
        self.assertTrue(text.startswith("2 stores nearest 94108:"))


if __name__ == "__main__":
    unittest.main()
