from datetime import date, datetime, time, timezone

from django.utils import timezone as django_timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import serializers

from .models import Edge, Node, RouteQuery


class StrictFloatField(serializers.FloatField):
    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")
        return super().to_internal_value(data)


class DateOrDateTimeField(serializers.Field):
    default_error_messages = {
        "invalid": "Use a date (YYYY-MM-DD) or an ISO 8601 datetime.",
    }

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        try:
            parsed = parse_date(data) or parse_datetime(data)
        except ValueError:
            parsed = None
        if parsed is None:
            self.fail("invalid")
        if isinstance(parsed, datetime) and django_timezone.is_naive(parsed):
            parsed = django_timezone.make_aware(parsed, timezone.utc)
        return parsed


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


class ShortestRouteRequestSerializer(serializers.Serializer):
    source = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )
    destination = serializers.SlugRelatedField(
        slug_field="name", queryset=Node.objects.all()
    )


class RouteQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteQuery
        fields = ["id", "source", "destination", "total_latency", "path", "created_at"]
        read_only_fields = fields


class RouteHistoryFilterSerializer(serializers.Serializer):
    source = serializers.CharField(required=False)
    destination = serializers.CharField(required=False)
    date_from = DateOrDateTimeField(required=False)
    date_to = DateOrDateTimeField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=1000)

    def validate(self, attrs):
        date_from = attrs.get("date_from")
        date_to = attrs.get("date_to")
        if isinstance(date_from, date) and not isinstance(date_from, datetime):
            attrs["date_from"] = datetime.combine(date_from, time.min, timezone.utc)
        if isinstance(date_to, date) and not isinstance(date_to, datetime):
            attrs["date_to"] = datetime.combine(date_to, time.max, timezone.utc)
        if "date_from" in attrs and "date_to" in attrs:
            if attrs["date_from"] > attrs["date_to"]:
                raise serializers.ValidationError(
                    {"date_from": "date_from must not be after date_to."}
                )
        return attrs
