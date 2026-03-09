# Keyword Search

SemPKM includes full-text keyword search powered by RDF4J LuceneSail. Search indexes all text values in your knowledge base -- not just object titles -- so you can find objects by any word or phrase that appears in their properties or body text.

## How Search Works

### The Lucene Index

Behind the scenes, RDF4J maintains an Apache Lucene index alongside the RDF triplestore. Whenever triples are added or updated in the current state graph (`urn:sempkm:current`), the Lucene index is updated automatically. The index covers:

- **Object titles** -- `dcterms:title` values (Notes, Projects)
- **Labels** -- `rdfs:label`, `skos:prefLabel`, `foaf:name` values
- **Body text** -- The Markdown body content of objects (`sempkm:body`)
- **Other literal values** -- Any string-valued property stored in the triplestore

This means a search for "quarterly" will match a Note titled "Q4 Planning" if its body contains the phrase "quarterly review" -- even though the word does not appear in the title.

### Indexing Scope

Search covers all objects in your current knowledge base (`urn:sempkm:current` graph). Event history, shape definitions, and ontology graphs are not included in search results. Only the live state of your data is searchable.

## Using Search

### Opening the Command Palette

Press **Alt+K** (or **F1**) to open the command palette. The palette appears as a centered overlay with a text input at the top.

### Searching

1. Start typing your search term in the palette input
2. Search activates after 2 characters
3. Results appear in the **Search** section of the palette as you type
4. The palette sends requests as you type (with a short debounce delay) so results update live

### Reading Results

Each search result shows three pieces of information:

- **Type icon** -- A small icon indicating the object type (Note, Person, Project, Concept, or other). This helps you quickly scan results when multiple types match.
- **Label** -- The object's primary label (its title, name, or preferred label depending on the type)
- **Snippet** -- A text excerpt showing the matching content, with the search term highlighted. The snippet is pulled from whichever property or body text matched the query.

### Opening a Result

- Use the **arrow keys** to navigate up and down through results
- Press **Enter** to open the selected object in the workspace as a new tab
- Alternatively, click any result with the mouse
- Press **Escape** to close the palette without opening anything

## Search Behavior

### Ranking

Results are ranked by Lucene relevance score. Objects where the search term appears in the title or label are ranked higher than objects where it appears only in the body text. Exact matches rank higher than partial matches.

### Partial Matches

Search supports partial word matching. Typing "plan" will match objects containing "planning", "planned", or "plan". This is handled by the Lucene index's default text analysis, which tokenizes and stems text values.

### Case Sensitivity

Search is **case-insensitive**. Searching for "alice", "Alice", or "ALICE" all return the same results.

### Special Characters

IRIs, punctuation, and special characters are tokenized by the Lucene analyzer. If you need to search for an exact IRI or a phrase containing special characters, the standard word-based search may not match. For exact IRI lookups, use the SPARQL Console instead (see [Chapter 21: SPARQL Console](21-sparql-console.md)).

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open command palette | **Alt+K** (or **F1**) |
| Navigate results | **Arrow keys** |
| Open selected object | **Enter** |
| Close palette | **Escape** |

## Tips

- **Use specific terms.** Broad searches like "the" or "note" will return many results. Use distinctive words from the content you are looking for.
- **Search by content, not just titles.** If you remember a phrase from a Note's body but not its title, search for that phrase -- the full-text index covers body text.
- **Combine with the navigation tree.** If search returns too many results, use the navigation tree to browse by type first, then search within a narrower mental context.
- **Check the snippet.** The highlighted snippet tells you which part of the object matched. If it shows body text, the title alone would not have helped you find it.

## Search vs. SPARQL

The command palette search and the SPARQL Console serve different purposes:

| Aspect | Keyword Search | SPARQL Console |
|--------|---------------|----------------|
| Access | **Alt+K** | **Alt+J** > SPARQL tab |
| Query style | Natural language keywords | Structured SPARQL queries |
| Best for | Quick lookup by remembered words | Complex filters, joins, aggregations |
| Results | Ranked list with snippets | Tabular data with exact values |
| Scope | Full-text index (labels + body) | All triples in the current graph |

Use keyword search when you know what you are looking for but not where it is. Use SPARQL when you need to answer structured questions about your data (e.g., "how many Notes were created this month?" or "which Projects have no related Persons?").

> **For Advanced Users:** The Lucene full-text index is accessible from SPARQL using the `luc:matches` predicate. This lets you combine keyword search with structured query patterns. For example, to find all Notes whose body contains "quarterly":
>
> ```sparql
> PREFIX luc: <http://www.ontotext.com/owlim/lucene#>
> SELECT ?note ?title WHERE {
>   ?note a sempkm:Note ;
>         dcterms:title ?title ;
>         luc:matches "quarterly" .
> }
> ```
>
> This is an advanced technique that combines the flexibility of SPARQL with the speed of Lucene indexing. The `luc:matches` predicate is provided by RDF4J's LuceneSail integration.

---

**Previous:** [Chapter 21: SPARQL Console](21-sparql-console.md) | **Next:** [Chapter 23: Virtual Filesystem (WebDAV)](23-vfs.md)
