from rest_framework.test import APITestCase

from network.models import Edge, Node, RouteQuery

URL = "/routes/shortest"


class ShortestRouteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        nodes = {name: Node.objects.create(name=name) for name in "ABCDE"}
        for source, destination, latency in [
            ("A", "B", 4),
            ("A", "C", 1),
            ("C", "B", 2),
            ("B", "D", 1),
            ("C", "D", 6),
        ]:
            Edge.objects.create(
                source=nodes[source], destination=nodes[destination], latency=latency
            )

    def post(self, data):
        return self.client.post(URL, data, format="json")

    def test_shortest_path(self):
        response = self.post({"source": "A", "destination": "D"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"total_latency": 4, "path": ["A", "C", "B", "D"]})

    def test_successful_query_is_saved(self):
        self.post({"source": "A", "destination": "D"})
        query = RouteQuery.objects.get()
        self.assertEqual(
            (query.source, query.destination, query.total_latency, query.path),
            ("A", "D", 4, ["A", "C", "B", "D"]),
        )

    def test_same_source_and_destination(self):
        response = self.post({"source": "A", "destination": "A"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"total_latency": 0, "path": ["A"]})

    def test_no_path_returns_404_and_is_not_saved(self):
        response = self.post({"source": "D", "destination": "A"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "No path exists between D and A"})
        self.assertFalse(RouteQuery.objects.exists())

    def test_isolated_node_returns_404(self):
        response = self.post({"source": "A", "destination": "E"})
        self.assertEqual(response.status_code, 404)

    def test_unknown_node_returns_400(self):
        response = self.post({"source": "A", "destination": "Z"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("destination", response.json())

    def test_missing_fields_return_400(self):
        response = self.post({})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {"source", "destination"})

    def test_total_is_rounded(self):
        x, y, z = (Node.objects.create(name=name) for name in "XYZ")
        Edge.objects.create(source=x, destination=y, latency=12.5)
        Edge.objects.create(source=y, destination=z, latency=10.9)
        response = self.post({"source": "X", "destination": "Z"})
        self.assertEqual(response.json()["total_latency"], 23.4)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(URL).status_code, 405)
