from rest_framework.test import APITestCase

from network.models import Node

URL = "/nodes"


class NodeTests(APITestCase):
    def post(self, data):
        return self.client.post(URL, data, format="json")

    def test_create(self):
        response = self.post({"name": "ServerA"})
        self.assertEqual(response.status_code, 201)
        node = Node.objects.get()
        self.assertEqual(response.json(), {"id": node.pk, "name": "ServerA"})

    def test_duplicate_name_returns_400(self):
        self.post({"name": "ServerA"})
        response = self.post({"name": "ServerA"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json())
        self.assertEqual(Node.objects.count(), 1)

    def test_names_are_case_sensitive(self):
        self.post({"name": "ServerA"})
        self.assertEqual(self.post({"name": "servera"}).status_code, 201)

    def test_invalid_names_return_400(self):
        for data in [{}, {"name": ""}, {"name": "   "}, {"name": None}, {"name": "x" * 256}]:
            with self.subTest(data=data):
                response = self.post(data)
                self.assertEqual(response.status_code, 400)
                self.assertIn("name", response.json())
        self.assertFalse(Node.objects.exists())

    def test_name_of_255_characters_is_allowed(self):
        self.assertEqual(self.post({"name": "x" * 255}).status_code, 201)

    def test_whitespace_is_trimmed(self):
        response = self.post({"name": "  ServerA  "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "ServerA")

    def test_trimmed_name_counts_as_duplicate(self):
        self.post({"name": "ServerA"})
        self.assertEqual(self.post({"name": " ServerA "}).status_code, 400)

    def test_id_is_read_only(self):
        response = self.post({"id": 999, "name": "ServerA"})
        self.assertEqual(response.status_code, 201)
        self.assertNotEqual(response.json()["id"], 999)

    def test_list_ordered_by_id(self):
        for name in ["ServerC", "ServerA", "ServerB"]:
            self.post({"name": name})
        response = self.client.get(URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [node["name"] for node in response.json()], ["ServerC", "ServerA", "ServerB"]
        )
        ids = [node["id"] for node in response.json()]
        self.assertEqual(ids, sorted(ids))

    def test_empty_list(self):
        self.assertEqual(self.client.get(URL).json(), [])
