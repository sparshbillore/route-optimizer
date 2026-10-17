from rest_framework import serializers

from .models import Edge, Node


class StrictFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
        return super().to_internal_value(data)


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ["id", "name"]
        read_only_fields = ["id"]


class EdgeSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )
    destination = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )
    latency = StrictFloatField()

    class Meta:
        model = Edge
        fields = ["id", "source", "destination", "latency"]
        read_only_fields = ["id"]
        validators = []

    def validate_latency(self, value):
        if value <= 0:
            raise serializers.ValidationError("Latency must be greater than 0.")
        return value

    def validate(self, attrs):
        source, destination = attrs["source"], attrs["destination"]
        if source == destination:
            raise serializers.ValidationError(
                {"destination": "Source and destination must be different nodes."}
            )
        if Edge.objects.filter(source=source, destination=destination).exists():
            raise serializers.ValidationError(
                f"Edge {source.name} → {destination.name} already exists."
            )
        return attrs
