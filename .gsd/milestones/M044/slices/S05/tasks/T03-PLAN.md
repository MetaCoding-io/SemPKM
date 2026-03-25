---
estimated_steps: 27
estimated_files: 2
skills_used: []
---

# T03: Replace guide.html copy-pasted buttons with data-driven chapter loop

Define a `GUIDE_CHAPTERS` data structure in `backend/app/shell/router.py` containing all chapter entries currently hardcoded as 55 `<button>` elements in `guide.html`. Pass this to the template context from `guide_page()`. Replace the hardcoded buttons with a Jinja2 `{% for %}` loop.

**Data structure design:**
```python
GUIDE_SECTIONS = [
    {
        "title": "Interactive Tutorials",
        "chapters": [
            {"title": "Welcome to SemPKM", "icon": "play-circle", "url": "/browser/?tour=welcome", "type": "tour"},
            {"title": "Creating Your First Object", "icon": "plus-circle", "url": "/browser/?tour=create-object", "type": "tour"},
        ],
    },
    {
        "title": "User Guide",
        "chapters": [
            {"filename": "01-what-is-sempkm.md", "title": "1. What is SemPKM?", "icon": "info"},
            # ... all chapters
        ],
    },
    # ... External References section
]
```

**Template pattern:** Each section renders its title as `<h3>`. Each chapter renders as a `<button>` with the same classes and attributes as the current hardcoded buttons. Tour-type chapters use a different `hx-get` URL pattern. External reference chapters open in new tabs.

**Three section types:**
1. Interactive Tutorials — use `hx-get="{{ ch.url }}"` (tour launch URLs)
2. User Guide chapters — use `hx-get="/guide/{{ ch.filename }}"` 
3. External References — use `onclick="window.open('{{ ch.url }}', '_blank')"` or similar

**Per KNOWLEDGE.md:** This only fixes `guide.html`. `docs/guide/README.md` and `docs/guide/index.html` remain manual. Note this in a code comment near `GUIDE_SECTIONS`.

## Inputs

- `backend/app/shell/router.py`
- `backend/app/templates/guide.html`

## Expected Output

- `backend/app/shell/router.py`
- `backend/app/templates/guide.html`

## Verification

grep -c 'docs-chapter-item' backend/app/templates/guide.html  # must be 0
wc -l backend/app/templates/guide.html | awk '{print ($1 < 80) ? "PASS" : "FAIL: " $1 " lines"}'
cd backend && python -m pytest tests/ -x -q  # all pass
