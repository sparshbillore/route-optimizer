from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("nodes", views.NodeListCreateView.as_view(), name="nodes"),
    path("edges", views.EdgeListCreateView.as_view(), name="edges"),
]
