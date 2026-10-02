"""URL routes for the feedback app."""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("feedback/", views.session_list, name="session_list"),
    path("feedback/<str:feedback_id>/", views.session_detail, name="session_detail"),
    # Token-protected ingest endpoint clients POST to.
    path("api/feedback", views.ingest, name="ingest"),
]
