"""SQLAlchemy ORM model for inference triple state tracking.

Tracks per-triple dismiss/promote state in SQLite. The triple_hash
is a deterministic SHA-256 of the (subject, predicate, object) N-Triples
representation, ensuring stable identifiers across inference runs.
"""

import hashlib

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InferenceTripleState(Base):
    """Per-triple state for inferred triples (active, dismissed, promoted).

    Each row tracks the status of an inferred triple across inference runs.
    The triple_hash serves as a stable identifier derived from the triple's
    subject, predicate, and object IRIs.
    """

    __tablename__ = "inference_triple_state"

    triple_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    subject_iri: Mapped[str] = mapped_column(Text)
    predicate_iri: Mapped[str] = mapped_column(Text)
    object_iri: Mapped[str] = mapped_column(Text)
    entailment_type: Mapped[str] = mapped_column(String(50))
    source_model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    inferred_at: Mapped[str] = mapped_column(String(50))
    dismissed_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    promoted_at: Mapped[str | None] = mapped_column(String(50), nullable=True)


def compute_triple_hash(s: str, p: str, o: str) -> str:
    """Compute a deterministic SHA-256 hash for a triple.

    Concatenates subject, predicate, and object as N-Triples-style strings
    (angle-bracket wrapped IRIs) and hashes the result.

    Args:
        s: Subject IRI string.
        p: Predicate IRI string.
        o: Object IRI string.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    canonical = f"<{s}> <{p}> <{o}>"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
