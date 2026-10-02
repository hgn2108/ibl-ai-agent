"""Views: a token-protected ingest API plus login-gated browsing/replay.

The ingest endpoint is the only public surface; it authenticates with a shared
bearer token (a write-only credential). All human-facing pages require a Django
login, so reviewers never need AWS/SSH access to read feedback.
"""

from __future__ import annotations

import hmac
import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import FeedbackSession

logger = logging.getLogger(__name__)


def _client_ip(request: HttpRequest) -> str:
    """Best-effort client IP, honoring a single proxy hop (nginx)."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _token_ok(request: HttpRequest) -> bool:
    """Constant-time comparison of the presented bearer token."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    prefix = "Bearer "
    if not header.startswith(prefix):
        return False
    return hmac.compare_digest(header[len(prefix):], settings.INGEST_TOKEN)


def _detail_url(request: HttpRequest, feedback_id: str) -> str:
    return request.build_absolute_uri(reverse("session_detail", args=[feedback_id]))


@csrf_exempt
@require_POST
def ingest(request: HttpRequest) -> JsonResponse:
    """Store a feedback payload submitted by a client (bearer-token auth)."""
    if not settings.INGEST_TOKEN:
        logger.error("Ingest attempted but IBL_FEEDBACK_INGEST_TOKEN is not configured.")
        return JsonResponse({"error": "server not configured for ingest"}, status=503)
    if not _token_ok(request):
        return JsonResponse({"error": "invalid or missing token"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({"error": "body must be valid JSON"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "payload must be a JSON object"}, status=400)

    feedback_id = payload.get("feedback_id")
    if not feedback_id or not isinstance(feedback_id, str):
        return JsonResponse({"error": "feedback_id is required"}, status=400)

    # Idempotent: a re-sent feedback_id is accepted without duplication.
    if FeedbackSession.objects.filter(feedback_id=feedback_id).exists():
        return JsonResponse(
            {"status": "duplicate", "feedback_id": feedback_id,
             "url": _detail_url(request, feedback_id)},
            status=200,
        )

    try:
        session = FeedbackSession.objects.create(
            feedback_id=feedback_id,
            client_created_at=str(payload.get("created_at", ""))[:40],
            message=str(payload.get("message", "")),
            host=str(payload.get("host", ""))[:32],
            schema_version=int(payload.get("schema_version", 0) or 0),
            agent=payload.get("agent") or {},
            environment=payload.get("environment") or {},
            redaction=payload.get("redaction") or {},
            transcript=payload.get("transcript") or [],
            transcript_raw=payload.get("transcript_raw") or [],
            size_bytes=len(request.body),
            remote_addr=_client_ip(request),
        )
    except (IntegrityError, ValueError, TypeError) as exc:
        logger.exception("Failed to store feedback %s", feedback_id)
        return JsonResponse({"error": f"could not store feedback: {exc}"}, status=400)

    logger.info("Stored feedback %s from host=%s", feedback_id, session.host)
    return JsonResponse(
        {"status": "stored", "feedback_id": feedback_id,
         "url": _detail_url(request, feedback_id)},
        status=201,
    )


@require_GET
def index(request: HttpRequest) -> HttpResponse:
    """Send the bare root to the session list."""
    return redirect("session_list")


@login_required
@require_GET
def session_list(request: HttpRequest) -> HttpResponse:
    """Paginated, searchable list of stored feedback sessions."""
    query = request.GET.get("q", "").strip()
    sessions = FeedbackSession.objects.all()
    if query:
        sessions = sessions.filter(
            Q(message__icontains=query)
            | Q(host__icontains=query)
            | Q(feedback_id__icontains=query)
        )
    page = Paginator(sessions, 25).get_page(request.GET.get("page"))
    return render(request, "feedback/list.html", {"page": page, "query": query})


@login_required
@require_GET
def session_detail(request: HttpRequest, feedback_id: str) -> HttpResponse:
    """Render one session's transcript as a chat replay."""
    session = get_object_or_404(FeedbackSession, feedback_id=feedback_id)
    return render(request, "feedback/detail.html", {"session": session})
