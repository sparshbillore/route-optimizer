from datetime import datetime, timezone

from rest_framework.test import APITestCase

from network.models import RouteQuery

URL = "/routes/history"


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


class RouteHistoryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for source, destination, created_at in [
            ("A", "B", utc(2026, 2, 19, 23, 59, 59)),
            ("A", "C", utc(2026, 2, 20, 0, 0, 0)),
            ("B", "C", utc(2026, 2, 20, 14, 32, 0)),
            ("A", "B", utc(2026, 2, 20, 23, 59, 59, 500000)),
            ("C", "A", utc(2026, 2, 21, 0, 0, 0)),
        ]:
            query = RouteQuery.objects.create(
                source=source, destination=destination, total_latency=1.5, path=[source, destination]
            )
            RouteQuery.objects.filter(pk=query.pk).update(created_at=created_at)

    def get(self, **params):
        return self.client.get(URL, params)

    def routes(self, response):
        self.assertEqual(response.status_code, 200)
        return [(r["source"], r["destination"]) for r in response.json()]

    def test_no_filters_returns_all_newest_first(self):
        self.assertEqual(
            self.routes(self.get()),
            [("C", "A"), ("A", "B"), ("B", "C"), ("A", "C"), ("A", "B")],
        )

    def test_response_shape(self):
        record = self.get(limit=1).json()[0]
        self.assertEqual(
            set(record), {"id", "source", "destination", "total_latency", "path", "created_at"}
        )
        self.assertEqual(record["created_at"], "2026-02-21T00:00:00Z")
        self.assertEqual(record["path"], ["C", "A"])
        self.assertEqual(record["total_latency"], 1.5)

    def test_filter_by_source(self):
        self.assertEqual(self.routes(self.get(source="A")), [("A", "B"), ("A", "C"), ("A", "B")])

    def test_filter_by_destination(self):
        self.assertEqual(self.routes(self.get(destination="C")), [("B", "C"), ("A", "C")])

    def test_source_filter_is_exact(self):
        self.assertEqual(self.routes(self.get(source="a")), [])

    def test_date_from_plain_date_starts_at_midnight(self):
        self.assertEqual(len(self.routes(self.get(date_from="2026-02-20"))), 4)

    def test_date_to_plain_date_includes_whole_day(self):
        self.assertEqual(len(self.routes(self.get(date_to="2026-02-20"))), 4)

    def test_same_day_range(self):
        self.assertEqual(
            self.routes(self.get(date_from="2026-02-20", date_to="2026-02-20")),
            [("A", "B"), ("B", "C"), ("A", "C")],
        )

    def test_datetime_bounds_are_inclusive(self):
        response = self.get(date_from="2026-02-20T14:32:00Z", date_to="2026-02-21T00:00:00Z")
        self.assertEqual(self.routes(response), [("C", "A"), ("A", "B"), ("B", "C")])

    def test_naive_datetime_is_treated_as_utc(self):
        self.assertEqual(self.routes(self.get(date_from="2026-02-21T00:00:00")), [("C", "A")])

    def test_datetime_with_offset(self):
        response = self.get(date_to="2026-02-20T05:30:00+05:30")
        self.assertEqual(self.routes(response), [("A", "C"), ("A", "B")])

    def test_combined_filters(self):
        response = self.get(source="A", destination="B", date_from="2026-02-20", limit=5)
        self.assertEqual(self.routes(response), [("A", "B")])

    def test_limit(self):
        self.assertEqual(self.routes(self.get(limit=2)), [("C", "A"), ("A", "B")])

    def test_limit_applies_after_filters(self):
        self.assertEqual(self.routes(self.get(source="A", limit=2)), [("A", "B"), ("A", "C")])

    def test_limit_larger_than_results(self):
        self.assertEqual(len(self.routes(self.get(limit=100))), 5)

    def test_bad_limit_returns_400(self):
        for value in ["abc", "0", "-5", "1.5", "1001"]:
            with self.subTest(limit=value):
                response = self.get(limit=value)
                self.assertEqual(response.status_code, 400)
                self.assertIn("limit", response.json())

    def test_bad_date_returns_400(self):
        for value in ["yesterday", "2026-13-01", "2026-02-30", "2026-02-20T25:00:00"]:
            for param in ["date_from", "date_to"]:
                with self.subTest(**{param: value}):
                    response = self.get(**{param: value})
                    self.assertEqual(response.status_code, 400)
                    self.assertIn(param, response.json())

    def test_date_from_after_date_to_returns_400(self):
        response = self.get(date_from="2026-02-21", date_to="2026-02-20")
        self.assertEqual(response.status_code, 400)
        self.assertIn("date_from", response.json())

    def test_empty_params_are_ignored(self):
        response = self.get(source="", destination="", date_from="", date_to="", limit="")
        self.assertEqual(len(self.routes(response)), 5)

    def test_empty_history(self):
        RouteQuery.objects.all().delete()
        self.assertEqual(self.routes(self.get()), [])

    def test_post_not_allowed(self):
        self.assertEqual(self.client.post(URL).status_code, 405)
