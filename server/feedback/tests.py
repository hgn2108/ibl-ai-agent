"""Tests for the feedback server: ingest auth + login-gated views."""

from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings

from .models import FeedbackSession

PAYLOAD = {
    "schema_version": 1,
    "feedback_id": "20260629T000000Z-deadbeef",
    "created_at": "2026-06-29T00:00:00Z",
    "message": "depth lookup returned wrong regions",
    "host": "codex",
    "agent": {"repo_commit": "abc1234"},
    "environment": {"os": "darwin"},
    "redaction": {"applied": True, "counts": {"secrets": 0, "paths": 1}},
    "transcript": [
        {"role": "user", "text": "find regions", "kind": "message"},
        {"role": "assistant", "text": "here you go", "kind": "message"},
    ],
    "transcript_raw": [{"x": 1}],
}


@override_settings(INGEST_TOKEN="testtoken")
class IngestTests(TestCase):
    def _post(self, token=None, data=None):
        extra = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token is not None else {}
        return self.client.post(
            "/api/feedback",
            data=json.dumps(PAYLOAD if data is None else data),
            content_type="application/json",
            **extra,
        )

    def test_missing_token_rejected(self):
        self.assertEqual(self._post().status_code, 401)

    def test_bad_token_rejected(self):
        self.assertEqual(self._post(token="wrong").status_code, 401)

    def test_valid_token_stores(self):
        resp = self._post(token="testtoken")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(FeedbackSession.objects.count(), 1)
        session = FeedbackSession.objects.get()
        self.assertEqual(session.feedback_id, PAYLOAD["feedback_id"])
        self.assertEqual(session.message_count, 2)
        self.assertGreater(session.size_bytes, 0)

    def test_duplicate_is_idempotent(self):
        self._post(token="testtoken")
        resp = self._post(token="testtoken")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "duplicate")
        self.assertEqual(FeedbackSession.objects.count(), 1)

    def test_bad_json_rejected(self):
        resp = self.client.post(
            "/api/feedback",
            data="not json",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer testtoken",
        )
        self.assertEqual(resp.status_code, 400)


@override_settings(INGEST_TOKEN="")
class IngestUnconfiguredTests(TestCase):
    def test_unconfigured_returns_503(self):
        resp = self.client.post(
            "/api/feedback",
            data="{}",
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer anything",
        )
        self.assertEqual(resp.status_code, 503)


class ViewAuthTests(TestCase):
    def setUp(self):
        self.session = FeedbackSession.objects.create(
            feedback_id="fid1",
            host="codex",
            message="hello world",
            transcript=[{"role": "user", "text": "ping", "kind": "message"}],
        )

    def test_list_requires_login(self):
        resp = self.client.get("/feedback/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_detail_requires_login(self):
        resp = self.client.get("/feedback/fid1/")
        self.assertEqual(resp.status_code, 302)

    def test_list_and_detail_after_login(self):
        User.objects.create_user("rev", password="pw-12345-ok")
        self.client.login(username="rev", password="pw-12345-ok")
        self.assertEqual(self.client.get("/feedback/").status_code, 200)
        detail = self.client.get("/feedback/fid1/")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "ping")  # transcript rendered
