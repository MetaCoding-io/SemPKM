# Keyword Search

SemPKM includes full-text keyword search powered by RDF4J LuceneSail. Search indexes all text values in your knowledge base -- not just object titles.

## Opening Search

Press **Ctrl+K** (or **Cmd+K** on macOS) to open the command palette, then start typing your search term.

Search activates after 2 characters and shows results in the **Search** section of the palette.

## Reading Results

Each result shows:
- **Type icon** -- indicates whether the object is a Note, Project, Person, Concept, or other type
- **Label** -- the object's title or name
- **Snippet** -- the matching text that triggered the result (highlighted from the index)

## Searching by Content

Search finds objects even when your keyword appears only in a property value, not the object's title. For example, searching "quarterly" will find a Note whose body contains "quarterly review" -- even if the Note is titled "Q4 Planning".

## Scope

Search covers all objects in your current knowledge base (`urn:sempkm:current` graph). Event history is not included in search results.

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Open command palette | Ctrl+K |
| Navigate results | Arrow keys |
| Open selected object | Enter |
| Close palette | Escape |

---

**Previous:** [Chapter 21: SPARQL Console](21-sparql-console.md) | **Next:** [Chapter 23: Virtual Filesystem (WebDAV)](23-vfs.md)
