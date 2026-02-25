# Chapter 6: Edges and Relationships

Knowledge does not live in isolated facts. A Note is written by a Person. A Concept belongs to a Project. A Person collaborates with another Person. These connections -- edges in graph terminology -- are what transform a collection of objects into a navigable knowledge graph.

This chapter explains what edges are in SemPKM, how they are created, and how you can browse the relationships between your objects.

---

## What Are Edges?

In SemPKM, an **edge** is a directed connection between two objects. Every edge has three essential components:

- **Source** -- the object where the edge originates
- **Target** -- the object the edge points to
- **Predicate** -- the type of relationship (e.g., "authored by", "related to", "part of")

Edges are stored as RDF triples in the triplestore, with the source as the subject, the predicate as the property, and the target as the object. This is the native language of the Semantic Web and gives SemPKM its power as a semantics-native platform.

### Typed vs. Untyped Links

SemPKM distinguishes between two kinds of connections:

**Typed edges** use predicates defined in a Mental Model's SHACL shapes. These are the reference properties you see in object forms -- for example, a Note shape might define an "Author" property with `sh:class` pointing to a Person type. Typed edges carry semantic meaning: the system knows that "Author" relates a Note to a Person, and it can use that information for validation, views, and graph layouts.

**First-class edge resources** go a step further. When created through the `edge.create` command, an edge becomes its own resource in the graph with its own IRI and type (`sempkm:Edge`). First-class edges support additional annotation properties beyond just source, target, and predicate. For example, you could annotate a "contributed to" edge with properties like "role" or "start date."

### Concrete Examples

Here are some typical edges in a Basic PKM knowledge base:

| Source | Predicate | Target | Meaning |
|--------|-----------|--------|---------|
| Meeting Notes (Note) | authored by | Alice (Person) | Alice wrote these meeting notes |
| Machine Learning (Concept) | related to | Neural Networks (Concept) | These concepts are related |
| API Redesign (Project) | involves | Bob (Person) | Bob is involved in this project |
| Research Paper (Note) | references | Deep Learning (Concept) | The note references this concept |
| Sprint 5 (Project) | part of | Product Roadmap (Project) | Sprint 5 is part of the roadmap |

These connections form a graph that you can traverse, query, and visualize.

---

## Creating Edges

### Using Reference Properties in Forms

The most common way to create an edge is through **reference properties** in an object's edit form. When a SHACL shape defines a property with a `sh:class` constraint, the form renders a search-as-you-type field for that property.

**Example: Linking a Note to its Author**

Suppose you are editing a Note and the form has an "Author" field that references the Person type:

1. Open the Note and enter edit mode (`Ctrl+E`)
2. In the "Author" field, start typing the person's name
3. SemPKM queries the triplestore for all Person instances matching your text
4. A **suggestions dropdown** appears below the field, showing matching results

<!-- Screenshot: reference search field with dropdown suggestions showing Person names -->

4. Click a suggestion to select it. The field displays the person's label, and the underlying IRI is stored in a hidden form field.
5. Save the object (`Ctrl+S`)

When you save, the property value is stored as a triple linking the Note to the Person via the "Author" predicate. This triple is an edge in the knowledge graph.

> **Tip:** Reference search filters results by the target type. If the "Author" field has `sh:class` pointing to Person, only Person instances appear in the dropdown. This prevents accidental type mismatches.

### Multi-Valued Reference Properties

Some reference properties allow multiple values (when `sh:maxCount` is unset or greater than 1). In this case, the form renders a list of reference fields with **Add** and **Remove** buttons:

1. The first reference input appears by default
2. Click **+ Add [Property Name]** to add another reference input
3. Each input has its own search-as-you-type functionality
4. Click the **X** button next to a reference input to remove it

This is useful for properties like "Contributors" (a Note can have multiple contributors) or "Related Concepts" (a Concept can be related to many others).

### How Edges Appear After Saving

When you save a reference property, the edge is created as an RDF triple in the current state graph. The system:

1. Commits the triple via the Event Store as part of an `object.patch` operation
2. Records the change as an immutable event in the event log
3. Triggers async validation to ensure the reference is valid

The edge immediately appears in the **Relations** panel on the right side of the workspace (see "Browsing Relationships" below).

### Creating Edges via the Command API

For advanced users or automation scenarios, edges can also be created programmatically through the Command API using the `edge.create` command:

```json
{
  "command": "edge.create",
  "params": {
    "source": "urn:sempkm:obj:note-abc123",
    "target": "urn:sempkm:obj:person-def456",
    "predicate": "urn:sempkm:model:basic-pkm:authoredBy",
    "properties": {
      "urn:sempkm:model:basic-pkm:role": "primary author"
    }
  }
}
```

This creates a first-class edge resource with its own IRI, typed as `sempkm:Edge`, with structural properties (source, target, predicate) and optional annotation properties (like "role" in the example above). Structural properties are immutable after creation; annotation properties can be updated via `edge.patch`.

See [The Command API](17-command-api.md) for full details.

---

## Browsing Relationships

### The Relations Panel

The primary way to browse an object's relationships is through the **Relations** section in the Details panel (right column of the workspace). When you select an object, SemPKM automatically queries the triplestore for all edges connected to it and displays them in two subsections.

<!-- Screenshot: relations panel showing outbound and inbound edges for a Note object -->

#### Outbound Edges

**Outbound** edges are relationships where the current object is the **source**. These are properties "pointing away" from the object. They are displayed grouped by predicate, with a right-arrow indicating the direction:

```
Outbound
  authored by
    -> Alice Johnson
    -> Bob Smith
  related to
    -> Machine Learning
```

Each target object is a clickable link. Click it to open that object in a new tab.

#### Inbound Edges

**Inbound** edges are relationships where the current object is the **target**. These are connections from other objects pointing to this one. They are displayed with a left-arrow:

```
Inbound
  references
    <- Research Paper: Introduction to AI
    <- Meeting Notes: Q4 Planning
  involves
    <- API Redesign Project
```

Inbound edges are particularly powerful for discovering how an object is used across your knowledge base. For example, viewing a Concept's inbound edges shows you every Note, Project, and other object that references it.

> **Note:** The `rdf:type` predicate is excluded from the Relations panel since it is a classification, not a relationship between your knowledge objects.

### Following Links

Browsing relationships is a navigation activity. The typical pattern is:

1. Open an object from the Explorer or command palette
2. Glance at the Relations panel to see its connections
3. Click a related object to open it in a new tab (or in a split group)
4. Continue following links to explore your knowledge graph

Each click opens the target object in the currently active editor group. If you want to keep the original object visible while exploring a related one, split the editor first (`Ctrl+\`) and click the link -- it opens in the active group while the other group keeps the original object.

### Graph View

For a visual, spatial exploration of relationships, use a **Graph View**. Graph views are defined in Mental Models and render objects as nodes and edges as connecting lines in an interactive visualization powered by Cytoscape.js.

To open a graph view:

1. Expand the **VIEWS** section in the Explorer panel
2. Find a graph view (indicated by the graph icon) under the relevant type group
3. Click to open it as a tab in the editor area

Alternatively, use the command palette (`Ctrl+K`) and search for "Browse: Graph:" followed by the view name.

<!-- Screenshot: graph view showing interconnected Notes, Concepts, People, and Projects -->

**Graph view features:**

- **Layout picker** -- choose from built-in layouts (force-directed, hierarchical, circular, grid) or model-specific layouts defined in the Mental Model
- **Fit button** -- resets the zoom and pan to fit all nodes in the viewport
- **Type-colored nodes** -- each node is colored by its RDF type, using the color scheme defined in the Mental Model
- **Interactive navigation** -- click a node to see its details; drag nodes to rearrange them; scroll to zoom
- **Filtering** -- search to filter which nodes are displayed

Graph views provide the "big picture" of your knowledge base that is hard to get from individual object views. They are especially useful for identifying clusters of related concepts, finding isolated objects that lack connections, and understanding the overall structure of a project or topic area.

---

## Edge Design Principles

Understanding a few design principles will help you work effectively with edges in SemPKM:

**Edges are directional.** "Note A authored by Person B" is different from "Person B authored Note A." The Relations panel shows this clearly by separating outbound and inbound connections.

**Edge predicates carry meaning.** The predicate is not just a label; it is a typed IRI from your Mental Model's vocabulary. This means the system can reason about relationships, validate them against SHACL constraints, and use them for intelligent views and queries.

**Edges are immutable once created.** When you create a first-class edge resource via the Command API, its source, target, and predicate cannot be changed. Only annotation properties (additional metadata on the edge) can be updated via `edge.patch`. To change a relationship, remove the old edge and create a new one.

**Reference properties are the simplest edge creation path.** For most users, setting reference properties in object forms is the natural and sufficient way to create edges. First-class edge resources with annotation properties are an advanced feature for cases where the relationship itself needs metadata.

**Every edge creates an event.** All edge operations (creation, annotation updates) are recorded as immutable events in the event log. You can view the diff for any edge operation and even undo it by creating a compensating event.

---

## Quick Reference

| Task | How |
|------|-----|
| Create an edge | Set a reference property in an object's edit form, then save |
| View an object's relationships | Select the object and check the Relations panel (right column) |
| Open a related object | Click its link in the Relations panel |
| See all relationships visually | Open a graph view from the Views section in the Explorer |
| Create an edge programmatically | Use the `edge.create` command via the Command API |
| Update edge annotations | Use the `edge.patch` command via the Command API |

---

**Next:** [Browsing and Visualizing Data](07-browsing-and-visualizing.md) covers table views, card views, and graph views in detail, including filtering, pagination, and renderer-specific features.
