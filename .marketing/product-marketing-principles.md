# SemPKM Product & Marketing Principles

These are durable principles that have recurred across SemPKM product thinking, market research, and competitor complaint analysis. They should guide product UX, onboarding, documentation, Mental Model design, and marketing language.

## 1. Never teach the RDF explanation before the user's ordinary-language model works

Users should first understand **objects, types, properties, relationships, and views** in ordinary language.

RDF, SHACL, SPARQL, ontology terms, IRIs, and other Semantic Web machinery explain *why SemPKM is rigorous and interoperable underneath*. They should not be prerequisites for using the product.

Prefer:

> A Paper is written by a Person.

before:

> `authoredBy` is an RDF object property whose range is `Person`.

The advanced explanation can always be available for users who want it.

## 2. Keep vocabulary simple and boring

Avoid inventing product-specific conceptual vocabulary where ordinary words already work.

Prefer a small stable set:

- **Object** — a thing worth describing or connecting independently.
- **Type** — what kind of thing an object is.
- **Property** — a value that describes an object.
- **Relationship** — how one object connects to another object.
- **View** — a way to select and display objects.
- **Mental Model** — a reusable model of a domain that supplies types, relationships, rules, views, and related behavior.

Semantic rigor should live underneath familiar language, not force users to learn a private ontology of application terminology.

## 3. Capture first. Structure when useful.

Structure must help thought rather than interrupt it.

A user should be able to capture an idea before deciding its final type, complete metadata, or place in a larger model. More structure can be added as its value becomes clear.

This is compatible with strong semantics: progressive formalization is not the absence of structure; it is allowing structure to emerge at the right time.

## 4. Keep properties and relationships conceptually distinct

A **property** describes an object with a value:

> Paper → publication date → 1962

A **relationship** connects one object to another object:

> Paper → authored by → Thomas Kuhn

Rule of thumb:

> If the value is something users may want to open, describe, query, or connect elsewhere, it probably deserves to be another object and therefore a relationship.

Do not collapse these concepts into ambiguous product terminology.

## 5. Plugins add powers. Mental Models add meaning.

Plugins primarily extend **what software can do**.

Mental Models define **what the user's information means**: what kinds of things exist in a domain, which properties describe them, how they relate, what constraints apply, and which views/workflows make sense.

This distinction is central to explaining why a reusable Research, CRM, Zettelkasten, or Business Planning Mental Model is not simply another plugin bundle.

## 6. Types describe identity; tags describe classification

A Type answers:

> **What kind of thing is this?**

A tag answers:

> **What cross-cutting classification applies to this thing?**

Example:

> *Dune* **is a Book** and may be tagged **science-fiction**.

A useful test:

> If changing the category changes which properties or relationships make sense, it probably deserves a Type. If it simply groups otherwise different objects, it is more likely a tag or view criterion.

## 7. Objects describe things, not locations

A folder primarily answers:

> **Where is this information?**

An object answers:

> **What thing does this information describe?**

An object can participate in many relationships and appear in many views without needing copies in multiple folders.

SemPKM should not frame this as "objects instead of files." The VFS provides a file/directory projection of the same semantic knowledge for users who want a filesystem interface.

## 8. Structure has to earn its cognitive cost

Users do not reject structure categorically. They reject structure that demands more thought than the work benefits from.

SemPKM should not attempt to convert users whose correct solution is simply fewer properties, fewer plugins, and fewer abstractions. The core beachhead is users whose work genuinely requires structured types and relationships.

## 9. Own the model; do not hand-build the machinery that enforces it

The target user may enjoy understanding and customizing their system. They do not necessarily want to maintain a bespoke stack of templates, YAML conventions, query plugins, validation plugins, scripts, and migrations just to keep that system coherent.

SemPKM should make the model explicit while taking responsibility for the infrastructure that applies it.

## 10. Preserve both human-readable access and semantic meaning

Plain files offer a powerful psychological and practical escape hatch. Rich semantic systems preserve meaning that flat exports often lose.

SemPKM should aim to provide both:

- RDF/SHACL/etc. preserve the semantic model.
- The VFS projects objects into human-readable Markdown files and directories through WebDAV.

The message is not "files are obsolete." It is:

> **Your knowledge can be semantic without giving up the file interface.**

## Short form

When a compact checklist is needed:

1. Never teach RDF before the ordinary-language model works.
2. Keep vocabulary simple and boring.
3. Capture first; structure when useful.
4. Keep properties and relationships distinct.
5. Plugins add powers; Mental Models add meaning.
6. Types describe identity; tags describe classification.
7. Objects describe things, not locations.
8. Structure must earn its cognitive cost.
9. Own the model; stop hand-building its enforcement machinery.
10. Preserve both human-readable access and semantic meaning.
