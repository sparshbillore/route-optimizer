from django.contrib import admin

from .models import Edge, Node, RouteQuery

admin.site.register(Node)
admin.site.register(Edge)
admin.site.register(RouteQuery)
