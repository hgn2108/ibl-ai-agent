"""Admin registration for raw browsing/management of feedback records."""

from __future__ import annotations

from django.contrib import admin

from .models import FeedbackSession


@admin.register(FeedbackSession)
class FeedbackSessionAdmin(admin.ModelAdmin):
    list_display = ("feedback_id", "host", "created_at", "message_preview", "message_count")
    list_filter = ("host", "created_at")
    search_fields = ("feedback_id", "message", "host")
    ordering = ("-created_at",)
    # Records are immutable once stored; show everything read-only.
    readonly_fields = (
        "feedback_id",
        "created_at",
        "client_created_at",
        "message",
        "host",
        "schema_version",
        "agent",
        "environment",
        "redaction",
        "transcript",
        "transcript_raw",
        "size_bytes",
        "remote_addr",
    )
