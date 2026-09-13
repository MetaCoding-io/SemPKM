"""Versioned Mental Model migrations.

A Mental Model carries a semver in its manifest. When that version changes,
the TBox (ontology, shapes, views, rules) can be swapped wholesale by
``ModelService.refresh_artifacts``, but instance data in
``urn:sempkm:current`` is left on the old schema. This module supplies the
missing half: declarative, versioned rewrites of the ABox that run when a
model is upgraded.

Migrations ship inside the archive, in the directory named by
``entrypoints.migrations``. Each file is named for the version it upgrades
**to**, so the runner can select a chain by semver::

    models/basic-pkm/
      manifest.yaml          # version: "3.0.0"
      migrations/
        2.1.0.yaml
        3.0.0.yaml

A migration is declarative YAML rather than raw SPARQL UPDATE, so that it can
be validated at install time and previewed before it runs::

    version: "3.0.0"
    description: Split Note into Note and Bookmark
    steps:
      - id: retype-url-notes
        kind: rename_class
        from: bpkm:Note
        to: bpkm:Bookmark
        where: "?s <urn:sempkm:model:basic-pkm:noteUrl> ?url ."

The load-bearing decision in this module is that **every step compiles to a
concrete delta**. Rather than executing ``DELETE/INSERT WHERE`` against the
current-state graph, each step runs a read-only ``SELECT`` that enumerates the
exact ``(s, p, o)`` triples to remove and to add. Those ground triples are
what the caller hands to the EventStore.

Three things follow from that:

* Event sourcing stays intact -- a migration is an ordinary event with an
  actor, visible in the event log, rather than an out-of-band rewrite.
* Preview is exact. A dry run is the same SELECT without the commit, so the
  operator sees real counts and sample rows instead of an estimate.
* The delta can be journalled, which is what makes a migration reversible.

Compilation never writes. Every query this module issues is a SELECT.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from packaging.version import InvalidVersion, Version
from rdflib import BNode, Literal, URIRef, Variable
from rdflib.namespace import RDF

from app.rdf.namespaces import CURRENT_GRAPH

if TYPE_CHECKING:  # pragma: no cover - imports for type checking only
    from app.models.manifest import ManifestSchema
    from app.triplestore.client import TriplestoreClient

logger = logging.getLogger(__name__)


# A migration filename must be exactly the target version.
MIGRATION_FILENAME_RE = re.compile(r"^(\d+\.\d+\.\d+)\.ya?ml$")

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# Upper bound on rows a single step may match. A step that exceeds it fails
# the whole migration rather than applying a silent partial delta.
MAX_STEP_ROWS = 50_000

# Upper bound on the combined delta of one migration file, counting deletes
# and inserts together.
MAX_MIGRATION_TRIPLES = 100_000

# How many sample rows a plan carries per step, for the preview UI.
PLAN_SAMPLE_SIZE = 5

STEP_KINDS = frozenset(
    {
        "rename_class",
        "rename_property",
        "drop_property",
        "set_default",
        "sparql",
    }
)

# Required and optional keys per step kind. Anything outside these sets is a
# validation error, so that a typo in a migration file fails loudly at install
# time instead of silently doing nothing to the user's data.
_STEP_SCHEMA: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "rename_class": (frozenset({"from", "to"}), frozenset({"where"})),
    "rename_property": (frozenset({"from", "to"}), frozenset({"where"})),
    "drop_property": (frozenset({"property"}), frozenset({"where"})),
    "set_default": (
        frozenset({"class", "property"}),
        frozenset({"value", "value_iri", "datatype", "lang", "where"}),
    ),
    "sparql": (frozenset({"where"}), frozenset({"delete", "insert"})),
}

_COMMON_STEP_KEYS = frozenset({"id", "kind", "description"})

# SPARQL keywords rejected inside an author-supplied fragment. A migration
# fragment is interpolated into a SELECT over urn:sempkm:current, so these
# would let it either escape that graph (GRAPH, SERVICE) or stop being
# read-only (the update forms). The archive is trusted code installed by an
# owner, but planning must stay side-effect free for preview to mean anything.
_FORBIDDEN_FRAGMENT_KEYWORDS = frozenset(
    {
        "graph",
        "service",
        "insert",
        "delete",
        "load",
        "clear",
        "drop",
        "create",
        "add",
        "move",
        "copy",
        "with",
        "using",
    }
)

_WORD_RE = re.compile(r"[A-Za-z_]+")

# Everything that carries author data rather than SPARQL syntax: string
# literals, angle-bracket IRIs, variables, and prefixed names. These are
# blanked before keyword scanning so that a property named e.g. `:dropDate`
# or a variable named `?graph` does not trip the keyword guard.
_NON_KEYWORD_TOKEN_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"'
    r"|'(?:[^'\\]|\\.)*'"
    r"|<[^<>]*>"
    r"|[?$][A-Za-z_]\w*"
    r"|[A-Za-z_][\w.-]*:[^\s{}()\[\],;.]*"
)


class MigrationError(Exception):
    """A migration file is malformed, or a migration cannot be applied."""


class MigrationTooLargeError(MigrationError):
    """A migration's delta exceeds the configured safety cap."""


@dataclass(frozen=True)
class MigrationStep:
    """One declarative rewrite within a migration file."""

    id: str
    kind: str
    params: dict
    description: str = ""

    @property
    def label(self) -> str:
        return self.description or f"{self.kind} ({self.id})"


@dataclass(frozen=True)
class MigrationSpec:
    """A parsed migration file, upgrading a model *to* ``version``."""

    version: str
    description: str
    steps: tuple[MigrationStep, ...]
    source: str

    @property
    def semver(self) -> Version:
        return Version(self.version)


@dataclass
class StepDelta:
    """The concrete triples one step would remove and add."""

    step_id: str
    kind: str
    label: str
    deletes: list[tuple] = field(default_factory=list)
    inserts: list[tuple] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.deletes and not self.inserts

    @property
    def affected_subjects(self) -> list[str]:
        subjects: list[str] = []
        seen: set[str] = set()
        for s, _p, _o in [*self.deletes, *self.inserts]:
            key = str(s)
            if key not in seen:
                seen.add(key)
                subjects.append(key)
        return subjects

    def samples(self, limit: int = PLAN_SAMPLE_SIZE) -> dict[str, list[str]]:
        """Human-readable sample rows for the preview UI."""

        def fmt(triples: list[tuple]) -> list[str]:
            return [f"{s} {p} {o}" for s, p, o in triples[:limit]]

        return {"deletes": fmt(self.deletes), "inserts": fmt(self.inserts)}


@dataclass
class MigrationDelta:
    """The compiled delta for one whole migration file."""

    version: str
    description: str
    steps: list[StepDelta] = field(default_factory=list)

    @property
    def delete_count(self) -> int:
        return sum(len(s.deletes) for s in self.steps)

    @property
    def insert_count(self) -> int:
        return sum(len(s.inserts) for s in self.steps)

    @property
    def total_triples(self) -> int:
        return self.delete_count + self.insert_count

    @property
    def is_empty(self) -> bool:
        return self.total_triples == 0

    def all_deletes(self) -> list[tuple]:
        out: list[tuple] = []
        for step in self.steps:
            out.extend(step.deletes)
        return out

    def all_inserts(self) -> list[tuple]:
        out: list[tuple] = []
        for step in self.steps:
            out.extend(step.inserts)
        return out

    def affected_subjects(self) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for step in self.steps:
            for subject in step.affected_subjects:
                if subject not in seen:
                    seen.add(subject)
                    ordered.append(subject)
        return ordered


# ---------------------------------------------------------------------------
# Term expansion and fragment validation
# ---------------------------------------------------------------------------


def expand_term(ref: str, prefixes: dict[str, str]) -> URIRef:
    """Expand a CURIE or absolute IRI from a migration file into a URIRef.

    ``bpkm:Note`` expands against the manifest's ``prefixes`` map.  Anything
    whose leading segment is not a declared prefix is treated as an absolute
    IRI, which is how ``urn:sempkm:...`` and ``http://...`` references keep
    working without being declared.

    Raises:
        MigrationError: If the reference is empty, contains whitespace or
            angle brackets, or uses an undeclared prefix that cannot be read
            as an absolute IRI.
    """
    if not isinstance(ref, str) or not ref.strip():
        raise MigrationError("Term reference must be a non-empty string")
    ref = ref.strip()
    if any(ch in ref for ch in ("<", ">", '"', " ", "\t", "\n")):
        raise MigrationError(f"Invalid characters in term reference: {ref!r}")

    if ":" not in ref:
        raise MigrationError(
            f"Term reference {ref!r} is neither a CURIE nor an absolute IRI"
        )

    prefix, _, local = ref.partition(":")
    if prefix in prefixes:
        return URIRef(f"{prefixes[prefix]}{local}")

    # Not a declared prefix. Accept it as an absolute IRI only if it looks
    # like a scheme we understand, so that a typo'd prefix is caught rather
    # than silently minting a nonsense IRI.
    if prefix in ("urn", "http", "https", "did", "file"):
        return URIRef(ref)

    raise MigrationError(
        f"Unknown prefix {prefix!r} in {ref!r}. Declare it in the manifest's "
        "prefixes map, or use an absolute IRI."
    )


def validate_fragment(fragment: str, *, field_name: str) -> str:
    """Check an author-supplied SPARQL group-graph-pattern fragment.

    The fragment is interpolated into a SELECT scoped to
    ``urn:sempkm:current``. This rejects the keywords that would let it leave
    that scope or stop being read-only, and rejects unbalanced braces, which
    would otherwise let a fragment close the enclosing GRAPH block.

    Returns:
        The stripped fragment.

    Raises:
        MigrationError: If the fragment is not a string or fails a check.
    """
    if not isinstance(fragment, str):
        raise MigrationError(f"{field_name} must be a string")
    text = fragment.strip()
    if not text:
        raise MigrationError(f"{field_name} must not be empty")

    if text.count("{") != text.count("}"):
        raise MigrationError(f"{field_name} has unbalanced braces")

    # Blank out literals, IRIs, variables and CURIEs first, so that only real
    # SPARQL keywords remain to be scanned.
    syntax_only = _NON_KEYWORD_TOKEN_RE.sub(" ", text)
    for word in _WORD_RE.findall(syntax_only):
        if word.lower() in _FORBIDDEN_FRAGMENT_KEYWORDS:
            raise MigrationError(
                f"{field_name} may not use the SPARQL keyword {word!r}. "
                "Migration fragments are read-only patterns scoped to the "
                "current-state graph."
            )
    return text


# ---------------------------------------------------------------------------
# Triple-pattern parsing for the `sparql` escape hatch
# ---------------------------------------------------------------------------

_TERM_RE = re.compile(
    r"""
    (?P<var>[?$][A-Za-z_][A-Za-z0-9_]*)
  | (?P<iri><[^<>"{}|^`\\\s]*>)
  | (?P<literal>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')
      (?:\^\^(?P<datatype><[^<>\s]*>|[A-Za-z_][\w.-]*:[^\s]*)
       |@(?P<lang>[A-Za-z]+(?:-[A-Za-z0-9]+)*))?
  | (?P<curie>[A-Za-z_][\w.-]*:[^\s.]*)
  | (?P<a>\ba\b)
    """,
    re.VERBOSE,
)


def parse_triple_pattern(text: str, prefixes: dict[str, str]) -> tuple:
    """Parse ``?s <p> ?o`` into a triple of rdflib terms.

    Supports variables, absolute IRIs, CURIEs, plain/typed/language literals,
    and ``a`` as shorthand for ``rdf:type``. A trailing ``.`` is optional.

    Raises:
        MigrationError: If the pattern is not exactly three terms.
    """
    if not isinstance(text, str):
        raise MigrationError("Triple pattern must be a string")
    stripped = text.strip().rstrip(".").strip()

    terms: list = []
    position = 0
    for match in _TERM_RE.finditer(stripped):
        if stripped[position : match.start()].strip():
            raise MigrationError(
                f"Unparseable text in triple pattern {text!r}: "
                f"{stripped[position:match.start()].strip()!r}"
            )
        position = match.end()
        terms.append(_term_from_match(match, prefixes))

    if stripped[position:].strip():
        raise MigrationError(
            f"Unparseable trailing text in triple pattern {text!r}: "
            f"{stripped[position:].strip()!r}"
        )
    if len(terms) != 3:
        raise MigrationError(
            f"Triple pattern must have exactly 3 terms, got {len(terms)}: {text!r}"
        )
    return tuple(terms)


def _term_from_match(match: re.Match, prefixes: dict[str, str]):
    if match.group("var"):
        return Variable(match.group("var")[1:])
    if match.group("iri"):
        return URIRef(match.group("iri")[1:-1])
    if match.group("a"):
        return RDF.type
    if match.group("curie"):
        return expand_term(match.group("curie"), prefixes)

    raw = match.group("literal")
    value = _unescape_literal(raw[1:-1])
    if match.group("lang"):
        return Literal(value, lang=match.group("lang"))
    if match.group("datatype"):
        datatype = match.group("datatype")
        if datatype.startswith("<"):
            return Literal(value, datatype=URIRef(datatype[1:-1]))
        return Literal(value, datatype=expand_term(datatype, prefixes))
    return Literal(value)


def _unescape_literal(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\r", "\r")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\'", "'")
        .replace("\\\\", "\\")
    )


# ---------------------------------------------------------------------------
# Parsing and discovery
# ---------------------------------------------------------------------------


def parse_migration_spec(path: Path) -> MigrationSpec:
    """Parse and validate one migration file.

    The filename is authoritative for the target version, and the ``version``
    key inside the file must agree with it. Keeping the two in sync means
    discovery can order files by name without reading them, and a rename can
    never silently retarget a migration.

    Raises:
        MigrationError: On any structural or semantic problem.
    """
    filename_match = MIGRATION_FILENAME_RE.match(path.name)
    if not filename_match:
        raise MigrationError(
            f"Migration filename {path.name!r} must be a semver target version, "
            "e.g. '2.1.0.yaml'"
        )
    file_version = filename_match.group(1)

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise MigrationError(f"Failed to parse {path.name}: {exc}") from exc
    except OSError as exc:
        raise MigrationError(f"Failed to read {path.name}: {exc}") from exc

    if not isinstance(raw, dict):
        raise MigrationError(f"{path.name} must contain a YAML mapping")

    unknown_top = set(raw) - {"version", "description", "steps"}
    if unknown_top:
        raise MigrationError(
            f"{path.name} has unknown top-level keys: {', '.join(sorted(unknown_top))}"
        )

    declared_version = raw.get("version")
    if declared_version != file_version:
        raise MigrationError(
            f"{path.name} declares version {declared_version!r} but its filename "
            f"targets {file_version!r}; the two must match"
        )

    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise MigrationError(f"{path.name} must declare a non-empty 'steps' list")

    steps: list[MigrationStep] = []
    seen_ids: set[str] = set()
    for index, raw_step in enumerate(raw_steps):
        step = _parse_step(raw_step, index, path.name)
        if step.id in seen_ids:
            raise MigrationError(
                f"{path.name} has a duplicate step id {step.id!r}"
            )
        seen_ids.add(step.id)
        steps.append(step)

    return MigrationSpec(
        version=file_version,
        description=str(raw.get("description") or ""),
        steps=tuple(steps),
        source=path.name,
    )


def _parse_step(raw_step, index: int, source: str) -> MigrationStep:
    where = f"{source} step {index}"
    if not isinstance(raw_step, dict):
        raise MigrationError(f"{where} must be a mapping")

    step_id = raw_step.get("id")
    if not isinstance(step_id, str) or not step_id.strip():
        raise MigrationError(f"{where} must declare a non-empty string 'id'")

    kind = raw_step.get("kind")
    if kind not in STEP_KINDS:
        raise MigrationError(
            f"{where} has unknown kind {kind!r}; expected one of "
            f"{', '.join(sorted(STEP_KINDS))}"
        )

    required, optional = _STEP_SCHEMA[kind]
    allowed = required | optional | _COMMON_STEP_KEYS
    present = set(raw_step)

    missing = required - present
    if missing:
        raise MigrationError(
            f"{where} ({kind}) is missing required keys: {', '.join(sorted(missing))}"
        )
    unknown = present - allowed
    if unknown:
        raise MigrationError(
            f"{where} ({kind}) has unknown keys: {', '.join(sorted(unknown))}"
        )

    params = {k: v for k, v in raw_step.items() if k not in _COMMON_STEP_KEYS}

    if kind == "set_default":
        has_value = "value" in params
        has_iri = "value_iri" in params
        if has_value == has_iri:
            raise MigrationError(
                f"{where} (set_default) must declare exactly one of "
                "'value' or 'value_iri'"
            )
        if has_iri and ("datatype" in params or "lang" in params):
            raise MigrationError(
                f"{where} (set_default) cannot combine 'value_iri' with "
                "'datatype' or 'lang'"
            )
        if "datatype" in params and "lang" in params:
            raise MigrationError(
                f"{where} (set_default) cannot declare both 'datatype' and 'lang'"
            )

    if kind == "sparql" and not (params.get("delete") or params.get("insert")):
        raise MigrationError(
            f"{where} (sparql) must declare at least one of 'delete' or 'insert'"
        )

    return MigrationStep(
        id=step_id.strip(),
        kind=kind,
        params=params,
        description=str(raw_step.get("description") or ""),
    )


def migrations_dir(model_dir: Path, manifest: "ManifestSchema") -> Path | None:
    """Resolve the archive's migrations directory, if it declares one.

    Raises:
        MigrationError: If the declared path escapes the archive, or is
            declared but is not a directory.
    """
    declared = manifest.entrypoints.migrations
    if declared is None:
        return None

    candidate = model_dir / declared
    root = model_dir.resolve()
    try:
        candidate.resolve().relative_to(root)
    except ValueError:
        raise MigrationError(
            f"Migrations path {declared!r} escapes the model directory"
        ) from None

    if not candidate.is_dir():
        raise MigrationError(
            f"Migrations directory not found: {candidate} "
            "(declared as entrypoints.migrations in manifest.yaml)"
        )
    return candidate


def discover_migrations(
    model_dir: Path, manifest: "ManifestSchema"
) -> list[MigrationSpec]:
    """Parse every migration in the archive, ordered by target version.

    Returns an empty list when the archive declares no migrations directory.

    Raises:
        MigrationError: If any file is malformed, two files target the same
            version, or a migration targets a version newer than the manifest.
    """
    directory = migrations_dir(model_dir, manifest)
    if directory is None:
        return []

    specs: list[MigrationSpec] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".yaml", ".yml"):
            continue
        specs.append(parse_migration_spec(path))

    by_version: dict[str, str] = {}
    for spec in specs:
        if spec.version in by_version:
            raise MigrationError(
                f"Two migration files target version {spec.version}: "
                f"{by_version[spec.version]} and {spec.source}"
            )
        by_version[spec.version] = spec.source

    manifest_version = Version(manifest.version)
    for spec in specs:
        if spec.semver > manifest_version:
            raise MigrationError(
                f"Migration {spec.source} targets version {spec.version}, which is "
                f"newer than the manifest version {manifest.version}"
            )

    specs.sort(key=lambda s: s.semver)
    return specs


def select_chain(
    specs: list[MigrationSpec], from_version: str, to_version: str
) -> list[MigrationSpec]:
    """Pick the migrations that carry a model from one version to another.

    A migration is in the chain when ``from_version < spec.version <=
    to_version``. A version bump with no migration file is legitimate -- it
    means the release changed no instance data -- so gaps are not an error.

    Raises:
        MigrationError: If either version is not valid semver, or the target
            is older than the installed version.
    """
    try:
        current = Version(from_version)
        target = Version(to_version)
    except InvalidVersion as exc:
        raise MigrationError(
            f"Cannot compare versions {from_version!r} and {to_version!r}: {exc}"
        ) from exc

    if target < current:
        raise MigrationError(
            f"Cannot migrate backwards, from {from_version} to {to_version}"
        )

    return [s for s in specs if current < s.semver <= target]


# ---------------------------------------------------------------------------
# Delta compilation
# ---------------------------------------------------------------------------


class MigrationCompiler:
    """Turns declarative steps into concrete triples, without writing.

    Every method here issues SELECT queries only. The caller decides whether
    to show the result as a preview or hand it to the EventStore.
    """

    def __init__(
        self,
        client: "TriplestoreClient",
        prefixes: dict[str, str],
        *,
        graph: str = CURRENT_GRAPH,
        max_step_rows: int = MAX_STEP_ROWS,
    ) -> None:
        self._client = client
        self._prefixes = dict(prefixes or {})
        self._graph = graph
        self._max_step_rows = max_step_rows

    async def compile_migration(self, spec: MigrationSpec) -> MigrationDelta:
        """Compile every step of one migration file into its delta."""
        delta = MigrationDelta(version=spec.version, description=spec.description)
        for step in spec.steps:
            delta.steps.append(await self.compile_step(step))

        if delta.total_triples > MAX_MIGRATION_TRIPLES:
            raise MigrationTooLargeError(
                f"Migration {spec.version} would change {delta.total_triples} "
                f"triples, above the cap of {MAX_MIGRATION_TRIPLES} "
                "(MAX_MIGRATION_TRIPLES). Split it into smaller migrations."
            )
        return delta

    async def compile_step(self, step: MigrationStep) -> StepDelta:
        """Compile one step into the triples it would remove and add."""
        handler = {
            "rename_class": self._compile_rename_class,
            "rename_property": self._compile_rename_property,
            "drop_property": self._compile_drop_property,
            "set_default": self._compile_set_default,
            "sparql": self._compile_sparql,
        }[step.kind]
        return await handler(step)

    # -- individual step kinds ------------------------------------------

    async def _compile_rename_class(self, step: MigrationStep) -> StepDelta:
        old = expand_term(step.params["from"], self._prefixes)
        new = expand_term(step.params["to"], self._prefixes)
        delta = self._new_delta(step)

        rows = await self._select(
            projection="?s",
            patterns=[f"?s a <{old}> ."],
            extra=step.params.get("where"),
            step=step,
        )
        for row in rows:
            subject = self._term(row, "s")
            delta.deletes.append((subject, RDF.type, old))
            delta.inserts.append((subject, RDF.type, new))
        return delta

    async def _compile_rename_property(self, step: MigrationStep) -> StepDelta:
        old = expand_term(step.params["from"], self._prefixes)
        new = expand_term(step.params["to"], self._prefixes)
        delta = self._new_delta(step)

        rows = await self._select(
            projection="?s ?o",
            patterns=[f"?s <{old}> ?o ."],
            extra=step.params.get("where"),
            step=step,
        )
        for row in rows:
            subject = self._term(row, "s")
            value = self._term(row, "o")
            delta.deletes.append((subject, old, value))
            delta.inserts.append((subject, new, value))
        return delta

    async def _compile_drop_property(self, step: MigrationStep) -> StepDelta:
        prop = expand_term(step.params["property"], self._prefixes)
        delta = self._new_delta(step)

        rows = await self._select(
            projection="?s ?o",
            patterns=[f"?s <{prop}> ?o ."],
            extra=step.params.get("where"),
            step=step,
        )
        for row in rows:
            delta.deletes.append((self._term(row, "s"), prop, self._term(row, "o")))
        return delta

    async def _compile_set_default(self, step: MigrationStep) -> StepDelta:
        cls = expand_term(step.params["class"], self._prefixes)
        prop = expand_term(step.params["property"], self._prefixes)
        delta = self._new_delta(step)

        if "value_iri" in step.params:
            value = expand_term(step.params["value_iri"], self._prefixes)
        elif "datatype" in step.params:
            datatype = expand_term(step.params["datatype"], self._prefixes)
            value = Literal(str(step.params["value"]), datatype=datatype)
        elif "lang" in step.params:
            value = Literal(str(step.params["value"]), lang=str(step.params["lang"]))
        else:
            value = Literal(str(step.params["value"]))

        rows = await self._select(
            projection="?s",
            patterns=[
                f"?s a <{cls}> .",
                f"FILTER NOT EXISTS {{ ?s <{prop}> ?existing }}",
            ],
            extra=step.params.get("where"),
            step=step,
        )
        for row in rows:
            delta.inserts.append((self._term(row, "s"), prop, value))
        return delta

    async def _compile_sparql(self, step: MigrationStep) -> StepDelta:
        """The escape hatch: bind a pattern, then substitute into templates.

        Even here the result is a concrete delta. The ``where`` clause binds
        variables, the ``delete``/``insert`` templates are instantiated once
        per binding, and any template that still contains an unbound variable
        after substitution is an error rather than a silently skipped row.
        """
        delta = self._new_delta(step)
        where = validate_fragment(step.params["where"], field_name="sparql.where")

        delete_templates = [
            parse_triple_pattern(t, self._prefixes)
            for t in _as_list(step.params.get("delete"), "sparql.delete")
        ]
        insert_templates = [
            parse_triple_pattern(t, self._prefixes)
            for t in _as_list(step.params.get("insert"), "sparql.insert")
        ]

        variables: list[str] = []
        for template in [*delete_templates, *insert_templates]:
            for term in template:
                if isinstance(term, Variable) and str(term) not in variables:
                    variables.append(str(term))
        if not variables:
            raise MigrationError(
                f"sparql step {step.id!r} has no variables to bind; its "
                "delete/insert templates are already ground"
            )

        projection = " ".join(f"?{name}" for name in variables)
        rows = await self._select(
            projection=f"DISTINCT {projection}",
            patterns=[where],
            extra=None,
            step=step,
        )

        for row in rows:
            bindings = {name: self._term(row, name) for name in variables}
            for template in delete_templates:
                delta.deletes.append(_substitute(template, bindings, step))
            for template in insert_templates:
                delta.inserts.append(_substitute(template, bindings, step))
        return delta

    # -- query plumbing --------------------------------------------------

    def _new_delta(self, step: MigrationStep) -> StepDelta:
        return StepDelta(step_id=step.id, kind=step.kind, label=step.label)

    async def _select(
        self,
        *,
        projection: str,
        patterns: list[str],
        extra: str | None,
        step: MigrationStep,
    ) -> list[dict]:
        """Run a read-only SELECT scoped to the migration's graph.

        Fetches one row beyond the cap so that an over-large step fails
        outright instead of applying a partial delta.
        """
        body = list(patterns)
        if extra is not None:
            body.append(validate_fragment(extra, field_name=f"step {step.id} where"))

        indented = "\n    ".join(body)
        sparql = (
            f"SELECT {projection} WHERE {{\n"
            f"  GRAPH <{self._graph}> {{\n"
            f"    {indented}\n"
            f"  }}\n"
            f"}} LIMIT {self._max_step_rows + 1}"
        )

        result = await self._client.query(sparql)
        rows = result.get("results", {}).get("bindings", [])
        if len(rows) > self._max_step_rows:
            raise MigrationTooLargeError(
                f"Step {step.id!r} matches more than {self._max_step_rows} rows "
                "(MAX_STEP_ROWS). Narrow it with a 'where' filter or split the "
                "migration."
            )
        return rows

    @staticmethod
    def _term(row: dict, name: str):
        """Rebuild an rdflib term from a SPARQL JSON binding."""
        binding = row.get(name)
        if binding is None:
            raise MigrationError(f"Query result is missing the ?{name} binding")

        kind = binding.get("type")
        value = binding.get("value", "")
        if kind == "uri":
            return URIRef(value)
        if kind == "bnode":
            return BNode(value)
        if binding.get("xml:lang"):
            return Literal(value, lang=binding["xml:lang"])
        if binding.get("datatype"):
            return Literal(value, datatype=URIRef(binding["datatype"]))
        return Literal(value)


def _as_list(value, field_name: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return value
    raise MigrationError(f"{field_name} must be a string or a list of strings")


def _substitute(template: tuple, bindings: dict, step: MigrationStep) -> tuple:
    out = []
    for term in template:
        if isinstance(term, Variable):
            name = str(term)
            if name not in bindings:
                raise MigrationError(
                    f"sparql step {step.id!r} uses ?{name}, which its where "
                    "clause does not bind"
                )
            out.append(bindings[name])
        else:
            out.append(term)
    return tuple(out)


__all__ = [
    "MAX_MIGRATION_TRIPLES",
    "MAX_STEP_ROWS",
    "MigrationCompiler",
    "MigrationDelta",
    "MigrationError",
    "MigrationSpec",
    "MigrationStep",
    "MigrationTooLargeError",
    "StepDelta",
    "discover_migrations",
    "expand_term",
    "migrations_dir",
    "parse_migration_spec",
    "parse_triple_pattern",
    "select_chain",
    "validate_fragment",
]
