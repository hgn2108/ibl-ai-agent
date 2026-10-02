"""Database models for stored feedback sessions."""

from __future__ import annotations

from django.db import models


class FeedbackSession(models.Model):
    """One submitted feedback bundle: a message plus a session transcript.

    The transcript fields are stored verbatim as JSON. They were already
    redacted client-side before upload, so the server treats them as opaque
    data to display, not to re-process.
    """

    # Client-generated identifier (sortable timestamp + random tail).
    feedback_id = models.CharField(max_length=64, unique=True, db_index=True)
    # When the server stored the record.
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # When the client built it (ISO-8601 string, kept as sent).
    client_created_at = models.CharField(max_length=40, blank=True)

    message = models.TextField(blank=True)
    host = models.CharField(max_length=32, blank=True)
    schema_version = models.IntegerField(default=0)

    # Structured blobs kept verbatim.
    agent = models.JSONField(default=dict, blank=True)
    environment = models.JSONField(default=dict, blank=True)
    redaction = models.JSONField(default=dict, blank=True)
    transcript = models.JSONField(default=list, blank=True)  # normalized messages
    transcript_raw = models.JSONField(default=list, blank=True)  # raw host records

    size_bytes = models.IntegerField(default=0)
    remote_addr = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.feedback_id} ({self.host})"

    @property
    def message_preview(self) -> str:
        """Short single-line preview of the message for list displays."""
        text = " ".join(self.message.split())
        return text[:120] + ("…" if len(text) > 120 else "")

    @property
    def message_count(self) -> int:
        """Number of normalized chat messages in the transcript."""
        return len(self.transcript) if isinstance(self.transcript, list) else 0
