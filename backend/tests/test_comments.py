"""Tests for comment backend: tree assembly, operation building, and soft-delete.

All tests are pure-function unit tests — no triplestore or server needed.
Tests cover _build_comment_tree(), _build_comment_create_operation(),
and _build_comment_delete_operation() from browser/comments.py.
"""

import pytest
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, XSD

from app.browser.comments import (
    _add_can_delete,
    _add_relative_times,
    _build_comment_create_operation,
    _build_comment_delete_operation,
    _build_comment_tree,
    _relative_time,
)
from app.rdf.namespaces import SEMPKM


# ── _build_comment_tree() ───────────────────────────────────────────


class TestBuildCommentTreeEmpty:
    """Empty input returns empty output."""

    def test_empty_list(self):
        assert _build_comment_tree([]) == []


class TestBuildCommentTreeSingle:
    """Single comment becomes the sole root."""

    def test_single_root(self):
        comments = [
            {
                "iri": "urn:c:1",
                "body": "Hello",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-01T00:00:00Z",
                "reply_to": None,
            }
        ]
        tree = _build_comment_tree(comments)
        assert len(tree) == 1
        assert tree[0]["iri"] == "urn:c:1"
        assert tree[0]["replies"] == []


class TestBuildCommentTreeFlat:
    """Multiple root comments (no replies) sorted by timestamp."""

    def test_flat_no_replies(self):
        comments = [
            {
                "iri": "urn:c:2",
                "body": "Second",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-02T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:1",
                "body": "First",
                "author": "urn:sempkm:user:bbb",
                "timestamp": "2026-01-01T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:3",
                "body": "Third",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-03T00:00:00Z",
                "reply_to": None,
            },
        ]
        tree = _build_comment_tree(comments)
        assert len(tree) == 3
        assert [c["iri"] for c in tree] == ["urn:c:1", "urn:c:2", "urn:c:3"]
        assert all(c["replies"] == [] for c in tree)


class TestBuildCommentTreeThreaded:
    """Parent comment with replies nested correctly."""

    def test_parent_with_replies(self):
        comments = [
            {
                "iri": "urn:c:1",
                "body": "Root",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-01T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:2",
                "body": "Reply A",
                "author": "urn:sempkm:user:bbb",
                "timestamp": "2026-01-02T00:00:00Z",
                "reply_to": "urn:c:1",
            },
            {
                "iri": "urn:c:3",
                "body": "Reply B",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-03T00:00:00Z",
                "reply_to": "urn:c:1",
            },
        ]
        tree = _build_comment_tree(comments)
        assert len(tree) == 1
        root = tree[0]
        assert root["iri"] == "urn:c:1"
        assert len(root["replies"]) == 2
        assert root["replies"][0]["iri"] == "urn:c:2"
        assert root["replies"][1]["iri"] == "urn:c:3"


class TestBuildCommentTreeDeepNesting:
    """Three levels of nesting: root → reply → reply-to-reply."""

    def test_deep_nesting(self):
        comments = [
            {
                "iri": "urn:c:1",
                "body": "Root",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-01T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:2",
                "body": "Level 2",
                "author": "urn:sempkm:user:bbb",
                "timestamp": "2026-01-02T00:00:00Z",
                "reply_to": "urn:c:1",
            },
            {
                "iri": "urn:c:3",
                "body": "Level 3",
                "author": "urn:sempkm:user:ccc",
                "timestamp": "2026-01-03T00:00:00Z",
                "reply_to": "urn:c:2",
            },
            {
                "iri": "urn:c:4",
                "body": "Level 4",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-04T00:00:00Z",
                "reply_to": "urn:c:3",
            },
        ]
        tree = _build_comment_tree(comments)
        assert len(tree) == 1
        assert tree[0]["iri"] == "urn:c:1"
        assert len(tree[0]["replies"]) == 1
        level2 = tree[0]["replies"][0]
        assert level2["iri"] == "urn:c:2"
        assert len(level2["replies"]) == 1
        level3 = level2["replies"][0]
        assert level3["iri"] == "urn:c:3"
        assert len(level3["replies"]) == 1
        assert level3["replies"][0]["iri"] == "urn:c:4"


class TestBuildCommentTreeMultipleRootsWithReplies:
    """Multiple root comments each with their own reply threads."""

    def test_interleaved_roots_and_replies(self):
        comments = [
            {
                "iri": "urn:c:1",
                "body": "Root A",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-01T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:2",
                "body": "Root B",
                "author": "urn:sempkm:user:bbb",
                "timestamp": "2026-01-02T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:3",
                "body": "Reply to A",
                "author": "urn:sempkm:user:ccc",
                "timestamp": "2026-01-03T00:00:00Z",
                "reply_to": "urn:c:1",
            },
            {
                "iri": "urn:c:4",
                "body": "Reply to B",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-04T00:00:00Z",
                "reply_to": "urn:c:2",
            },
            {
                "iri": "urn:c:5",
                "body": "Another reply to A",
                "author": "urn:sempkm:user:bbb",
                "timestamp": "2026-01-05T00:00:00Z",
                "reply_to": "urn:c:1",
            },
        ]
        tree = _build_comment_tree(comments)
        assert len(tree) == 2

        root_a = tree[0]
        assert root_a["iri"] == "urn:c:1"
        assert len(root_a["replies"]) == 2
        assert root_a["replies"][0]["iri"] == "urn:c:3"
        assert root_a["replies"][1]["iri"] == "urn:c:5"

        root_b = tree[1]
        assert root_b["iri"] == "urn:c:2"
        assert len(root_b["replies"]) == 1
        assert root_b["replies"][0]["iri"] == "urn:c:4"


class TestBuildCommentTreeOrphanedReply:
    """Reply to a non-existent parent is treated as a root."""

    def test_orphaned_reply_becomes_root(self):
        comments = [
            {
                "iri": "urn:c:1",
                "body": "Normal root",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-01T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:2",
                "body": "Orphan reply",
                "author": "urn:sempkm:user:bbb",
                "timestamp": "2026-01-02T00:00:00Z",
                "reply_to": "urn:c:missing",
            },
        ]
        tree = _build_comment_tree(comments)
        assert len(tree) == 2
        assert tree[0]["iri"] == "urn:c:1"
        assert tree[1]["iri"] == "urn:c:2"


class TestBuildCommentTreeTimestampSorting:
    """Replies within the same parent are sorted by timestamp."""

    def test_replies_sorted_by_timestamp(self):
        comments = [
            {
                "iri": "urn:c:1",
                "body": "Root",
                "author": "urn:sempkm:user:aaa",
                "timestamp": "2026-01-01T00:00:00Z",
                "reply_to": None,
            },
            {
                "iri": "urn:c:late",
                "body": "Late reply",
                "author": "urn:sempkm:user:bbb",
                "timestamp": "2026-01-10T00:00:00Z",
                "reply_to": "urn:c:1",
            },
            {
                "iri": "urn:c:early",
                "body": "Early reply",
                "author": "urn:sempkm:user:ccc",
                "timestamp": "2026-01-02T00:00:00Z",
                "reply_to": "urn:c:1",
            },
        ]
        tree = _build_comment_tree(comments)
        replies = tree[0]["replies"]
        assert replies[0]["iri"] == "urn:c:early"
        assert replies[1]["iri"] == "urn:c:late"


# ── _build_comment_create_operation() ────────────────────────────────


class TestBuildCommentCreateOperation:
    """Verify triples and structure of create operations."""

    def test_top_level_comment(self):
        author_uri = URIRef("urn:sempkm:user:abc-123")
        op = _build_comment_create_operation(
            comment_iri="https://example.org/data/Comment/test-1",
            object_iri="https://example.org/data/Note/my-note",
            body="Great note!",
            author_uri=author_uri,
            reply_to=None,
        )

        assert op.operation_type == "comment.create"
        assert "https://example.org/data/Comment/test-1" in op.affected_iris
        assert "https://example.org/data/Note/my-note" in op.affected_iris

        comment = URIRef("https://example.org/data/Comment/test-1")
        object_ref = URIRef("https://example.org/data/Note/my-note")

        # Check required triples
        assert (comment, RDF.type, SEMPKM.Comment) in op.data_triples
        assert (comment, SEMPKM.commentOn, object_ref) in op.data_triples
        assert (comment, SEMPKM.commentBody, Literal("Great note!")) in op.data_triples
        assert (comment, SEMPKM.commentedBy, author_uri) in op.data_triples

        # Timestamp triple exists (can't check exact value)
        timestamp_triples = [
            t for t in op.data_triples if t[1] == SEMPKM.commentedAt
        ]
        assert len(timestamp_triples) == 1
        assert timestamp_triples[0][2].datatype == XSD.dateTime

        # No replyTo triple for top-level comment
        reply_triples = [t for t in op.data_triples if t[1] == SEMPKM.replyTo]
        assert len(reply_triples) == 0

        # Materialize inserts mirror data triples
        assert op.materialize_inserts == op.data_triples
        assert op.materialize_deletes == []

    def test_reply_comment(self):
        author_uri = URIRef("urn:sempkm:user:abc-123")
        op = _build_comment_create_operation(
            comment_iri="https://example.org/data/Comment/reply-1",
            object_iri="https://example.org/data/Note/my-note",
            body="I agree!",
            author_uri=author_uri,
            reply_to="https://example.org/data/Comment/parent-1",
        )

        comment = URIRef("https://example.org/data/Comment/reply-1")
        parent = URIRef("https://example.org/data/Comment/parent-1")

        # replyTo triple present for reply
        assert (comment, SEMPKM.replyTo, parent) in op.data_triples

        # Parent included in affected IRIs
        assert "https://example.org/data/Comment/parent-1" in op.affected_iris

    def test_operation_has_correct_description(self):
        author_uri = URIRef("urn:sempkm:user:abc-123")
        op = _build_comment_create_operation(
            comment_iri="https://example.org/data/Comment/test-2",
            object_iri="https://example.org/data/Note/target",
            body="Test",
            author_uri=author_uri,
        )
        assert "https://example.org/data/Note/target" in op.description


# ── _build_comment_delete_operation() ────────────────────────────────


class TestBuildCommentDeleteOperation:
    """Verify soft-delete operation structure."""

    def test_soft_delete_replaces_body_removes_author(self):
        op = _build_comment_delete_operation(
            comment_iri="https://example.org/data/Comment/c1",
            old_body="Original text",
            old_author="urn:sempkm:user:abc-123",
        )

        assert op.operation_type == "comment.delete"
        assert "https://example.org/data/Comment/c1" in op.affected_iris

        comment = URIRef("https://example.org/data/Comment/c1")

        # Should insert "[deleted]" body
        assert (
            comment,
            SEMPKM.commentBody,
            Literal("[deleted]"),
        ) in op.materialize_inserts

        # Should delete old body
        assert (
            comment,
            SEMPKM.commentBody,
            Literal("Original text"),
        ) in op.materialize_deletes

        # Should delete old author
        assert (
            comment,
            SEMPKM.commentedBy,
            URIRef("urn:sempkm:user:abc-123"),
        ) in op.materialize_deletes

    def test_soft_delete_preserves_data_triples_for_event(self):
        """The event graph records the new body for audit trail."""
        op = _build_comment_delete_operation(
            comment_iri="https://example.org/data/Comment/c2",
            old_body="Some text",
            old_author="urn:sempkm:user:def-456",
        )

        comment = URIRef("https://example.org/data/Comment/c2")
        assert (
            comment,
            SEMPKM.commentBody,
            Literal("[deleted]"),
        ) in op.data_triples

    def test_soft_delete_description(self):
        op = _build_comment_delete_operation(
            comment_iri="https://example.org/data/Comment/c3",
            old_body="Body",
            old_author="urn:sempkm:user:xyz",
        )
        assert "c3" in op.description


# ── Relative time tests ─────────────────────────────────────────────


class TestRelativeTime:
    """Tests for _relative_time() human-readable timestamp conversion."""

    def test_just_now(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        assert _relative_time(now) == "just now"

    def test_minutes_ago(self):
        from datetime import datetime, timedelta, timezone
        ts = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        assert _relative_time(ts) == "5 minutes ago"

    def test_one_minute_ago(self):
        from datetime import datetime, timedelta, timezone
        ts = (datetime.now(timezone.utc) - timedelta(minutes=1, seconds=10)).isoformat()
        assert _relative_time(ts) == "1 minute ago"

    def test_hours_ago(self):
        from datetime import datetime, timedelta, timezone
        ts = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        assert _relative_time(ts) == "3 hours ago"

    def test_yesterday(self):
        from datetime import datetime, timedelta, timezone
        ts = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        assert _relative_time(ts) == "yesterday"

    def test_days_ago(self):
        from datetime import datetime, timedelta, timezone
        ts = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        assert _relative_time(ts) == "5 days ago"

    def test_weeks_ago(self):
        from datetime import datetime, timedelta, timezone
        ts = (datetime.now(timezone.utc) - timedelta(weeks=3)).isoformat()
        assert _relative_time(ts) == "3 weeks ago"

    def test_invalid_returns_original(self):
        assert _relative_time("not-a-date") == "not-a-date"

    def test_empty_returns_original(self):
        assert _relative_time("") == ""


# ── Can-delete tests ────────────────────────────────────────────────


class TestAddCanDelete:
    """Tests for _add_can_delete() flag computation."""

    def test_author_can_delete_own_comment(self):
        comments = [{"body": "hi", "author": "urn:sempkm:user:alice", "replies": []}]
        _add_can_delete(comments, "urn:sempkm:user:alice", "member")
        assert comments[0]["can_delete"] is True

    def test_non_author_member_cannot_delete(self):
        comments = [{"body": "hi", "author": "urn:sempkm:user:alice", "replies": []}]
        _add_can_delete(comments, "urn:sempkm:user:bob", "member")
        assert comments[0]["can_delete"] is False

    def test_owner_can_delete_any(self):
        comments = [{"body": "hi", "author": "urn:sempkm:user:alice", "replies": []}]
        _add_can_delete(comments, "urn:sempkm:user:bob", "owner")
        assert comments[0]["can_delete"] is True

    def test_deleted_comment_cannot_be_deleted_again(self):
        comments = [{"body": "[deleted]", "author": None, "replies": []}]
        _add_can_delete(comments, "urn:sempkm:user:alice", "owner")
        assert comments[0]["can_delete"] is False

    def test_recursive_on_replies(self):
        reply = {"body": "reply", "author": "urn:sempkm:user:bob", "replies": []}
        comments = [{"body": "root", "author": "urn:sempkm:user:alice", "replies": [reply]}]
        _add_can_delete(comments, "urn:sempkm:user:bob", "member")
        assert comments[0]["can_delete"] is False
        assert reply["can_delete"] is True


class TestAddRelativeTimes:
    """Tests for _add_relative_times() recursive enrichment."""

    def test_adds_relative_time_to_flat(self):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        comments = [{"timestamp": now, "replies": []}]
        _add_relative_times(comments)
        assert "relative_time" in comments[0]
        assert comments[0]["relative_time"] == "just now"

    def test_recursive_on_replies(self):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        reply = {"timestamp": (now - timedelta(hours=2)).isoformat(), "replies": []}
        comments = [{"timestamp": now.isoformat(), "replies": [reply]}]
        _add_relative_times(comments)
        assert comments[0]["relative_time"] == "just now"
        assert reply["relative_time"] == "2 hours ago"
