# Virtual Filesystem (WebDAV)

SemPKM exposes your knowledge base as a read-only virtual filesystem over WebDAV. You can mount it in your operating system's file manager and browse your objects as Markdown files -- no API calls or browser required.

## How It Works

The WebDAV endpoint at `/dav/` presents your knowledge base as a directory tree:

```
/dav/
  basic-pkm/
    Note/
      My First Note.md
      Weekly Review.md
    Project/
      Website Redesign.md
    Person/
      Alice Smith.md
    Concept/
      Knowledge Graph.md
```

Each Mental Model becomes a top-level folder. Inside each model folder, objects are grouped by type. Each object is a Markdown file with YAML frontmatter containing its metadata.

## Generating an API Token

WebDAV uses HTTP Basic authentication. Your password is an API token, not your account password.

1. Log in to SemPKM in your browser
2. Open **Settings** from the sidebar
3. Under **API Tokens**, click **Generate Token**
4. Give it a name (e.g., "Finder mount") and copy the token

You can also generate a token via the API:

```bash
curl -X POST http://localhost:3901/api/auth/tokens \
  -H "Content-Type: application/json" \
  -H "Cookie: sempkm_session=<your-session-cookie>" \
  -d '{"name": "WebDAV mount"}'
```

The token is shown exactly once -- save it somewhere safe.

## Connecting from macOS (Finder)

1. Open **Finder**
2. Press **Cmd+K** or go to **Go > Connect to Server**
3. Enter the server address:
   - Local development: `http://localhost:3901/dav/`
   - Production: `https://your-domain.com/dav/`
4. Click **Connect**
5. When prompted for credentials:
   - **Name:** your SemPKM email address
   - **Password:** your API token

The knowledge base appears as a mounted drive in Finder's sidebar.

## Connecting from Windows

1. Open **File Explorer**
2. Right-click **This PC** and select **Map Network Drive**
3. Enter the folder path:
   - `http://localhost:3901/dav/` (local) or `https://your-domain.com/dav/` (production)
4. Check **Connect using different credentials**
5. Enter your SemPKM email and API token when prompted

Alternatively, use the command line:

```cmd
net use Z: http://localhost:3901/dav/ /user:you@example.com YOUR_TOKEN
```

## Connecting from Linux

### Nautilus (GNOME Files)

1. Open **Files**
2. Click **Other Locations** in the sidebar
3. In the **Connect to Server** field at the bottom, enter:
   - `dav://localhost:3901/dav/` (local) or `davs://your-domain.com/dav/` (production)
4. Enter your email and API token when prompted

### Command Line (cadaver)

```bash
cadaver http://localhost:3901/dav/
# Username: you@example.com
# Password: <your API token>
```

### Mount via davfs2

```bash
sudo mount -t davfs http://localhost:3901/dav/ /mnt/sempkm
# Enter email and token when prompted
```

## File Format

Each object is rendered as a Markdown file with YAML frontmatter:

```markdown
---
type_iri: "urn:sempkm:model:basic-pkm:Note"
object_iri: "urn:sempkm:object:abc123"
label: "My First Note"
properties:
  created: "2026-01-15"
  modified: "2026-02-20"
---

This is the body content of the note, pulled from the object's
body property in the knowledge graph.
```

The frontmatter contains:

| Field | Description |
|-------|-------------|
| `type_iri` | The full IRI of the object's RDF type |
| `object_iri` | The full IRI of this specific object |
| `label` | The display name of the object |
| `properties` | Additional RDF properties as key-value pairs |

The body text (below the `---` separator) comes from the object's body property, if one exists.

## Directory Structure

```
/dav/
  {model-id}/           # One folder per installed Mental Model
    {type-label}/       # One folder per type defined in the model
      {object-label}.md # One file per object of that type
```

- **Model folders** correspond to installed Mental Models (e.g., `basic-pkm`)
- **Type folders** correspond to SHACL node shapes in the model (e.g., `Note`, `Project`, `Person`, `Concept`)
- **Object files** are named after the object's label, with a `.md` extension

## Caching

Directory listings are cached for 30 seconds to reduce load on the triplestore. If you create or modify an object in the browser, it may take up to 30 seconds to appear in the mounted filesystem.

## Read-Only Access

The WebDAV mount is **read-only** in this version. You can browse and read files, but you cannot create, edit, or delete objects through the filesystem. Attempting to write returns an error.

Write support is planned for a future release.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 401 Unauthorized | Invalid or expired token | Generate a new API token |
| Empty directories | No objects of that type exist | Create objects in the browser first |
| Stale file listing | Cache has not expired yet | Wait up to 30 seconds, then refresh |
| Cannot connect | Wrong URL or port | Verify the `/dav/` path is included in the URL |
| macOS "connection failed" | macOS prefers HTTPS for WebDAV | Use `http://` explicitly for local dev |

---

**Previous:** [Chapter 22: Keyword Search](22-keyword-search.md) | **Next:** [Chapter 24: Obsidian Onboarding](24-obsidian-onboarding.md)
