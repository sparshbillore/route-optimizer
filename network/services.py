import heapq
from collections import defaultdict


def shortest_path(edges, start, end):
    graph = defaultdict(list)
    for source, destination, latency in edges:
        graph[source].append((destination, latency))

    dist = {start: 0.0}
    prev = {}
    heap = [(0.0, start)]

    while heap:
        distance, node = heapq.heappop(heap)
        if node == end:
            path = [end]
            while path[-1] != start:
                path.append(prev[path[-1]])
            return distance, path[::-1]
        if distance > dist[node]:
            continue
        for neighbour, latency in graph[node]:
            candidate = distance + latency
            if candidate < dist.get(neighbour, float("inf")):
                dist[neighbour] = candidate
                prev[neighbour] = node
                heapq.heappush(heap, (candidate, neighbour))

    return None
