from django.test import SimpleTestCase

from network.services import shortest_path

EXAMPLE = [
    ("A", "B", 4),
    ("A", "C", 1),
    ("C", "B", 2),
    ("B", "D", 1),
    ("C", "D", 6),
]


class ShortestPathTests(SimpleTestCase):
    def test_example_graph(self):
        self.assertEqual(shortest_path(EXAMPLE, "A", "D"), (4, ["A", "C", "B", "D"]))

    def test_cheaper_indirect_route_beats_direct_edge(self):
        self.assertEqual(shortest_path(EXAMPLE, "A", "B"), (3, ["A", "C", "B"]))

    def test_single_edge(self):
        self.assertEqual(shortest_path(EXAMPLE, "A", "C"), (1, ["A", "C"]))

    def test_start_equals_end(self):
        self.assertEqual(shortest_path(EXAMPLE, "A", "A"), (0, ["A"]))

    def test_start_equals_end_with_no_edges(self):
        self.assertEqual(shortest_path([], "A", "A"), (0, ["A"]))

    def test_unreachable_destination(self):
        self.assertIsNone(shortest_path(EXAMPLE, "D", "A"))

    def test_edges_are_directed(self):
        self.assertIsNone(shortest_path([("A", "B", 1)], "B", "A"))

    def test_disconnected_components(self):
        edges = [("A", "B", 1), ("C", "D", 1)]
        self.assertIsNone(shortest_path(edges, "A", "D"))

    def test_no_edges(self):
        self.assertIsNone(shortest_path([], "A", "B"))

    def test_dead_end_node_does_not_crash(self):
        edges = [("A", "X", 1), ("A", "B", 5)]
        self.assertEqual(shortest_path(edges, "A", "B"), (5, ["A", "B"]))

    def test_cycle(self):
        edges = [("A", "B", 1), ("B", "A", 1), ("B", "C", 1), ("C", "A", 1)]
        self.assertEqual(shortest_path(edges, "A", "C"), (2, ["A", "B", "C"]))

    def test_stale_heap_entries_are_skipped(self):
        edges = [
            ("A", "B", 10),
            ("A", "C", 1),
            ("C", "B", 1),
            ("B", "D", 20),
        ]
        self.assertEqual(shortest_path(edges, "A", "D"), (22, ["A", "C", "B", "D"]))

    def test_float_latencies(self):
        total, path = shortest_path([("A", "B", 12.5), ("B", "C", 10.9)], "A", "C")
        self.assertAlmostEqual(total, 23.4)
        self.assertEqual(path, ["A", "B", "C"])
