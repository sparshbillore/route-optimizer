from rest_framework.test import APITestCase

from network.models import Edge, Node

URL = "/edges"


class EdgeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        Node.objects.create(name="ServerA")
        Node.objects.create(name="ServerB")

    def post(self, data):
        return self.client.post(URL, data, format="json")

    def edge(self, source="ServerA", destination="ServerB", latency=12.5):
        return {"source": source, "destination": destination, "latency": latency}

    def test_create(self):
        response = self.post(self.edge())
        self.assertEqual(response.status_code, 201)
        edge = Edge.objects.get()
        self.assertEqual(
            response.json(),
            {"id": edge.pk, "source": "ServerA", "destination": "ServerB", "latency": 12.5},
        )

    def test_duplicate_returns_400_with_message(self):
        self.post(self.edge())
        response = self.post(self.edge(latency=3))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(), {"non_field_errors": ["Edge ServerA → ServerB already exists."]}
        )
        self.assertEqual(Edge.objects.get().latency, 12.5)

    def test_reverse_edge_is_allowed(self):
        self.post(self.edge())
        response = self.post(self.edge(source="ServerB", destination="ServerA"))
        self.assertEqual(response.status_code, 201)

    def test_self_loop_returns_400(self):
        response = self.post(self.edge(destination="ServerA"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("destination", response.json())

    def test_invalid_latency_returns_400(self):
        for latency in [0, -1, "abc", True, False, None, "NaN", "Infinity"]:
            with self.subTest(latency=latency):
                response = self.post(self.edge(latency=latency))
                self.assertEqual(response.status_code, 400)
                self.assertIn("latency", response.json())
        self.assertFalse(Edge.objects.exists())

    def test_small_positive_latency_is_allowed(self):
        self.assertEqual(self.post(self.edge(latency=0.001)).status_code, 201)

    def test_unknown_node_returns_400(self):
        for field in ["source", "destination"]:
            with self.subTest(field=field):
                response = self.post({**self.edge(), field: "ServerZ"})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json())

    def test_missing_field_returns_400(self):
        for field in ["source", "destination", "latency"]:
            with self.subTest(field=field):
                data = self.edge()
                del data[field]
                response = self.post(data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(list(response.json()), [field])

    def test_list(self):
        self.post(self.edge())
        self.post(self.edge(source="ServerB", destination="ServerA", latency=7))
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(e["source"], e["destination"], e["latency"]) for e in response.json()],
            [("ServerA", "ServerB", 12.5), ("ServerB", "ServerA", 7)],
        )
