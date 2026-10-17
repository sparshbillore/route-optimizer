from rest_framework.test import APITestCase

from network.models import Edge, Node, RouteQuery


class DeleteTests(APITestCase):
    def setUp(self):
        self.nodes = {name: Node.objects.create(name=name) for name in "ABCD"}
        self.edges = {
            (source, destination): Edge.objects.create(
                source=self.nodes[source],
                destination=self.nodes[destination],
                latency=latency,
            )
            for source, destination, latency in [
                ("A", "B", 1),
                ("B", "D", 1),
                ("A", "C", 5),
                ("C", "D", 5),
            ]
        }

    def shortest(self, source, destination):
        return self.client.post(
            "/routes/shortest",
            {"source": source, "destination": destination},
            format="json",
        )

    def test_get_node(self):
        node = self.nodes["A"]
        response = self.client.get(f"/nodes/{node.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": node.pk, "name": "A"})

    def test_get_edge(self):
        edge = self.edges[("A", "B")]
        response = self.client.get(f"/edges/{edge.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"id": edge.pk, "source": "A", "destination": "B", "latency": 1.0},
        )

    def test_delete_node(self):
        response = self.client.delete(f"/nodes/{self.nodes['A'].pk}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Node.objects.filter(name="A").exists())

    def test_delete_node_removes_its_edges(self):
        self.client.delete(f"/nodes/{self.nodes['B'].pk}")
        self.assertEqual(
            set(Edge.objects.values_list("source__name", "destination__name")),
            {("A", "C"), ("C", "D")},
        )

    def test_delete_node_keeps_history(self):
        self.assertEqual(self.shortest("A", "D").status_code, 200)
        self.client.delete(f"/nodes/{self.nodes['A'].pk}")
        history = self.client.get("/routes/history").json()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["path"], ["A", "B", "D"])

    def test_deleted_node_can_no_longer_be_routed(self):
        self.client.delete(f"/nodes/{self.nodes['A'].pk}")
        self.assertEqual(self.shortest("A", "D").status_code, 400)

    def test_delete_edge(self):
        edge = self.edges[("A", "B")]
        response = self.client.delete(f"/edges/{edge.pk}")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Edge.objects.filter(pk=edge.pk).exists())
        self.assertTrue(Node.objects.filter(name="A").exists())
        self.assertTrue(Node.objects.filter(name="B").exists())

    def test_delete_edge_switches_to_next_best_path(self):
        self.assertEqual(self.shortest("A", "D").json()["path"], ["A", "B", "D"])
        self.client.delete(f"/edges/{self.edges[('A', 'B')].pk}")
        self.assertEqual(
            self.shortest("A", "D").json(),
            {"total_latency": 10, "path": ["A", "C", "D"]},
        )

    def test_delete_last_route_returns_404(self):
        self.client.delete(f"/edges/{self.edges[('A', 'B')].pk}")
        self.client.delete(f"/edges/{self.edges[('A', 'C')].pk}")
        response = self.shortest("A", "D")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"error": "No path exists between A and D"})

    def test_deleted_edge_can_be_recreated(self):
        self.client.delete(f"/edges/{self.edges[('A', 'B')].pk}")
        response = self.client.post(
            "/edges",
            {"source": "A", "destination": "B", "latency": 2},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

    def test_unknown_ids_return_404(self):
        for url in ["/nodes/999", "/edges/999"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.delete(url).status_code, 404)
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_deleting_twice_returns_404(self):
        url = f"/edges/{self.edges[('A', 'B')].pk}"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_delete_without_id_not_allowed(self):
        for url in ["/nodes", "/edges"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(Node.objects.count(), 4)
        self.assertEqual(Edge.objects.count(), 4)

    def test_non_integer_id_returns_404(self):
        self.assertEqual(self.client.delete("/nodes/abc").status_code, 404)

    def test_detail_routes_do_not_allow_updates(self):
        url = f"/nodes/{self.nodes['A'].pk}"
        self.assertEqual(self.client.put(url, {"name": "Z"}, format="json").status_code, 405)
        self.assertEqual(self.client.patch(url, {"name": "Z"}, format="json").status_code, 405)
