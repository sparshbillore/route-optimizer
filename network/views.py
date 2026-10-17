from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Edge, Node, RouteQuery
from .serializers import (
    EdgeSerializer,
    NodeSerializer,
    ShortestRouteRequestSerializer,
)
from .services import shortest_path


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class NodeListCreateView(generics.ListCreateAPIView):
    queryset = Node.objects.order_by("id")
    serializer_class = NodeSerializer


class EdgeListCreateView(generics.ListCreateAPIView):
    queryset = Edge.objects.select_related("source", "destination").order_by("id")
    serializer_class = EdgeSerializer


@api_view(["POST"])
def shortest_route(request):
    serializer = ShortestRouteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    source = serializer.validated_data["source"].name
    destination = serializer.validated_data["destination"].name

    edges = Edge.objects.values_list("source__name", "destination__name", "latency")
    result = shortest_path(edges, source, destination)
    if result is None:
        return Response(
            {"error": f"No path exists between {source} and {destination}"},
            status=status.HTTP_404_NOT_FOUND,
        )

    total, path = result
    total = round(total, 6)
    RouteQuery.objects.create(
        source=source, destination=destination, total_latency=total, path=path
    )
    return Response({"total_latency": total, "path": path})
