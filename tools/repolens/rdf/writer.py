"""A small Turtle writer.

repolens has no dependency beyond PyYAML, and adding rdflib to emit a file
whose shape we fully control would be a poor trade. What we emit has no blank
nodes and no collections, so the hard parts of Turtle do not arise; what does
arise is escaping, and that is done properly here rather than hopefully.
"""

from __future__ import annotations

from urllib.parse import quote

# The order matters: the backslash rule has to run first or it re-escapes the
# backslashes the later rules introduce.
_ESCAPES = [("\\", "\\\\"), ('"', '\\"'), ("\n", "\\n"), ("\r", "\\r"), ("\t", "\\t")]


def escape_literal(text: str) -> str:
    for a, b in _ESCAPES:
        text = text.replace(a, b)
    return text


def slug(text: str) -> str:
    """A path-ish string safe to sit inside an IRI."""
    return quote(str(text), safe="/._-")


class TurtleWriter:
    """Accumulates triples and serialises them grouped by subject."""

    def __init__(self, prefixes: dict[str, str], base: str) -> None:
        self.prefixes = dict(prefixes)
        self.base = base
        self._order: list[str] = []
        self._by_subject: dict[str, list[tuple[str, str]]] = {}

    # ---- term construction -------------------------------------------------

    def iri(self, *segments: str) -> str:
        """An IRI under this graph's base, from slugged segments."""
        return "<" + self.base + "/".join(slug(s) for s in segments if s != "") + ">"

    @staticmethod
    def ref(iri: str) -> str:
        """An absolute IRI written in full."""
        return "<" + iri + ">"

    @staticmethod
    def text(value: str) -> str:
        return '"' + escape_literal(str(value)) + '"'

    @staticmethod
    def integer(value) -> str:
        return f'"{int(value)}"^^xsd:integer'

    @staticmethod
    def decimal(value) -> str:
        return f'"{float(value)}"^^xsd:decimal'

    @staticmethod
    def boolean(value) -> str:
        return "true" if value else "false"

    @staticmethod
    def datetime(value: str) -> str:
        return f'"{escape_literal(value)}"^^xsd:dateTime'

    # ---- accumulation ------------------------------------------------------

    def add(self, subject: str, predicate: str, obj: str | None) -> None:
        if obj is None or subject is None:
            return
        if subject not in self._by_subject:
            self._by_subject[subject] = []
            self._order.append(subject)
        self._by_subject[subject].append((predicate, obj))

    def add_text(self, subject: str, predicate: str, value) -> None:
        """Skip empty strings rather than emitting a triple that says nothing."""
        if value is None or value == "":
            return
        self.add(subject, predicate, self.text(value))

    @property
    def triple_count(self) -> int:
        return sum(len(v) for v in self._by_subject.values())

    @property
    def subject_count(self) -> int:
        return len(self._order)

    # ---- output ------------------------------------------------------------

    def serialise(self, header: str = "") -> str:
        out: list[str] = []
        if header:
            out += ["# " + line for line in header.splitlines()]
            out.append("")
        for prefix, iri in self.prefixes.items():
            out.append(f"@prefix {prefix}: <{iri}> .")
        out.append("")
        for subject in self._order:
            pairs = self._by_subject[subject]
            out.append(subject)
            for i, (p, o) in enumerate(pairs):
                end = " ." if i == len(pairs) - 1 else " ;"
                out.append(f"    {p} {o}{end}")
            out.append("")
        return "\n".join(out)
