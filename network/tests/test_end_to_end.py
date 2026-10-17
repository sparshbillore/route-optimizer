from rest_framework.test import APITestCase


class EndToEndTests(APITestCase):
    def post(self, url, data):
        response = self.client.post(url, data, format="json")
        return response.status_code, response.json()

    def test_full_flow(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

        for name in ["ServerA", "ServerB", "ServerC", "ServerD"]:
            status, _ = self.post("/nodes", {"name": name})
            self.assertEqual(status, 201)

        for source, destination, latency in [
            ("ServerA", "ServerB", 12.5),
            ("ServerB", "ServerC", 10.9),
            ("ServerA", "ServerC", 30),
            ("ServerC", "ServerD", 5),
        ]:
            status, _ = self.post(
                "/edges", {"source": source, "destination": destination, "latency": latency}
            )
            self.assertEqual(status, 201)

        status, body = self.post(
            "/routes/shortest", {"source": "ServerA", "destination": "ServerD"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            {"total_latency": 28.4, "path": ["ServerA", "ServerB", "ServerC", "ServerD"]},
        )

        status, body = self.post(
            "/routes/shortest", {"source": "ServerD", "destination": "ServerA"}
        )
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "No path exists between ServerD and ServerA"})

        history = self.client.get("/routes/history").json()
        self.assertEqual(len(history), 1)
        self.assertEqual(
            {key: history[0][key] for key in ["source", "destination", "total_latency", "path"]},
            {
                "source": "ServerA",
                "destination": "ServerD",
                "total_latency": 28.4,
                "path": ["ServerA", "ServerB", "ServerC", "ServerD"],
            },
        )
        self.assertRegex(history[0]["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
