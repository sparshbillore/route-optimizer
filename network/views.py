from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Node
from .serializers import NodeSerializer


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class NodeListCreateView(generics.ListCreateAPIView):
    queryset = Node.objects.order_by("id")
    serializer_class = NodeSerializer
